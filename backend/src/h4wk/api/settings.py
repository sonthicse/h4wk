"""API Settings (T32): nguồn thu, nhà cung cấp AI, API key. Key chỉ gửi lên; response chỉ
có bản che. Mọi thao tác ghi có audit nhưng không ghi giá trị key."""

import re
from datetime import datetime
from time import perf_counter
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from h4wk.ai.base import ProviderError, ProviderRequest
from h4wk.ai.providers import key_name, make_provider
from h4wk.api.deps import current_actor
from h4wk.collectors import quota, registry
from h4wk.collectors.models import Cap
from h4wk.collectors.orchestrator import Settings as RouteSettings
from h4wk.collectors.providers import supadata
from h4wk.core import audit, secrets, settings
from h4wk.core.config_models import AiConfig, ModelCaps, Route, SourcesConfig
from h4wk.core.db import SourceStateRow, as_aware, get_engine
from h4wk.core.secrets import KeyInfo
from h4wk.core.types import VN_TZ, VnDatetime

router = APIRouter(prefix="/api/settings", tags=["settings"])
ActorDep = Annotated[str, Depends(current_actor)]
SourceName = Literal["ytdlp", "youtube_api", "supadata"]
PROVIDER_NAME = re.compile(r"^[a-z0-9_-]{1,32}$")


class SourceUsage(BaseModel):
    used: int
    limit: int
    period: Literal["day", "month"]
    resets_at: VnDatetime | None


class SourceInfo(BaseModel):
    name: SourceName
    enabled: bool
    fault_injection: bool  # bật thì nguồn bị coi như bị chặn (giả lập cho demo)
    needs_key: bool
    key: KeyInfo | None
    implemented: bool  # đã có adapter
    status: Literal["active", "paused"]
    paused_until: VnDatetime | None
    consecutive_failures: int
    last_error: str | None
    last_error_at: VnDatetime | None
    usage: SourceUsage | None  # youtube_api (theo ngày), supadata (theo kỳ thanh toán)


class SourcesSettings(BaseModel):
    sources: list[SourceInfo]
    priority: dict[Cap, list[SourceName]]
    uncovered: list[Cap]  # loại dữ liệu không còn nguồn nào đang bật và đã có adapter


class SourcePatch(BaseModel):
    enabled: bool | None = None
    fault_injection: bool | None = None


class SourcesUpdate(BaseModel):
    sources: dict[SourceName, SourcePatch] = {}
    priority: dict[Cap, list[SourceName]] | None = None  # có thì thay toàn bộ


class KeyBody(BaseModel):
    value: str = Field(min_length=1)


class TestResult(BaseModel):
    ok: bool
    detail: str
    latency_ms: int | None = None


class ProviderInfo(BaseModel):
    name: str
    type: Literal["anthropic", "openai_compat", "gemini"]
    base_url: str | None
    models: dict[str, ModelCaps]
    key: KeyInfo


class AiSettings(BaseModel):
    providers: list[ProviderInfo]
    tasks: dict[str, list[Route]]


class AiUpdate(BaseModel):
    providers: dict[str, dict[str, Any]] | None = None  # có thì thay toàn bộ
    tasks: dict[str, list[dict[str, str]]] | None = None  # có thì thay toàn bộ


def _invalid(e: ValidationError) -> HTTPException:
    errors = [{"loc": list(err["loc"]), "msg": err["msg"]} for err in e.errors()]
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, errors)


# ------------------------------------------------------------------- nguồn thu


def _usage(name: str, now: datetime) -> SourceUsage | None:
    if name == "supadata":
        c = supadata.credits_usage()
        return (
            SourceUsage(used=c.used, limit=c.limit, period="month", resets_at=None) if c else None
        )
    if name != "youtube_api":
        return None
    u = quota.usage(now)
    return SourceUsage(used=u.used, limit=u.limit, period="day", resets_at=u.resets_at)


def _sources_view() -> SourcesSettings:
    cfg = settings.load_sources()
    sections = cfg.sources.model_dump()
    collectors = {n: make() for n, make in registry.COLLECTORS.items()}
    route = RouteSettings.from_sources(cfg, list(collectors))
    now = datetime.now(VN_TZ)
    with Session(get_engine()) as s:
        states = {n: s.get(SourceStateRow, n) for n in sections}
    out = []
    for name, sec in sections.items():
        st = states[name]
        until = as_aware(st.suspended_until) if st and st.suspended_until else None
        paused = until is not None and until > now
        key = settings.SOURCE_KEYS.get(name)
        out.append(
            SourceInfo(
                name=name,
                enabled=sec["enabled"],
                fault_injection=sec["fault_injection"],
                needs_key=key is not None,
                key=secrets.info(key) if key else None,
                implemented=name in collectors,
                status="paused" if paused else "active",
                paused_until=until if paused else None,
                consecutive_failures=st.consecutive_failures if st else 0,
                last_error=st.last_error if st else None,
                last_error_at=as_aware(st.last_error_at) if st and st.last_error_at else None,
                usage=_usage(name, now),
            )
        )
    uncovered = [
        cap
        for cap in Cap
        if not any(
            n in collectors and cap in collectors[n].capabilities and sections[n]["enabled"]
            for n in route.priority[cap]
            if n in sections
        )
    ]
    priority = {cap: [str(n) for n in names] for cap, names in cfg.priority.items()}
    return SourcesSettings(sources=out, priority=priority, uncovered=uncovered)  # type: ignore[arg-type]


@router.get("/sources")
def get_sources() -> SourcesSettings:
    return _sources_view()


@router.put("/sources")
def put_sources(body: SourcesUpdate, actor: ActorDep) -> SourcesSettings:
    data = settings.load_sources().model_dump(mode="json", by_alias=True, exclude_none=True)
    for name, patch in body.sources.items():
        data["sources"][name].update(patch.model_dump(exclude_none=True))
    if body.priority is not None:
        data["priority"] = {str(k): v for k, v in body.priority.items()}
    try:
        cfg = SourcesConfig.model_validate(data)
    except ValidationError as e:
        audit.log(actor, "settings.sources", None, {"error": "invalid"}, status="error")
        raise _invalid(e) from None
    settings.save_sources(cfg)
    audit.log(actor, "settings.sources", None, body.model_dump(mode="json", exclude_none=True))
    return _sources_view()


def _source_key(name: str) -> str:
    key = settings.SOURCE_KEYS.get(name)
    if key is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{name} has no API key")
    return key


@router.put("/sources/{name}/key")
def put_source_key(name: SourceName, body: KeyBody, actor: ActorDep) -> KeyInfo:
    key = _source_key(name)
    secrets.put(key, body.value)
    audit.log(actor, "settings.key.set", key)
    return secrets.info(key)


@router.delete("/sources/{name}/key")
def delete_source_key(name: SourceName, actor: ActorDep) -> KeyInfo:
    key = _source_key(name)
    secrets.delete(key)
    audit.log(actor, "settings.key.delete", key)
    return secrets.info(key)


@router.post("/sources/{name}/test")
def test_source(name: SourceName, actor: ActorDep) -> TestResult:
    make = registry.COLLECTORS.get(name)
    if make is None:
        result = TestResult(ok=False, detail="not implemented yet")
    else:
        start = perf_counter()
        try:
            health = make().health_check()
            result = TestResult(ok=health.ok, detail=health.detail)
        except Exception as e:
            result = TestResult(ok=False, detail=str(e))
        result.latency_ms = int((perf_counter() - start) * 1000)
    audit.log(actor, "settings.sources.test", name, {"ok": result.ok})
    return result


@router.post("/sources/{name}/resume")
def resume_source(name: SourceName, actor: ActorDep) -> SourceInfo:
    with Session(get_engine()) as s:
        row = s.get(SourceStateRow, name)
        if row is not None:
            row.suspended_until, row.consecutive_failures = None, 0
            s.add(row)
            s.commit()
    audit.log(actor, "settings.sources.resume", name)
    return next(x for x in _sources_view().sources if x.name == name)


# --------------------------------------------------------------------------- AI


def _ai_view() -> AiSettings:
    cfg = settings.load_ai()
    return AiSettings(
        providers=[
            ProviderInfo(
                name=name,
                type=p.type,
                base_url=str(p.base_url) if p.base_url else None,
                models=p.models,
                key=secrets.info(key_name(name)),
            )
            for name, p in cfg.providers.items()
        ],
        tasks={str(t): routes for t, routes in cfg.tasks.items()},
    )


@router.get("/ai")
def get_ai() -> AiSettings:
    return _ai_view()


def _drop_key(provider: str, actor: str) -> None:
    """Xoá key trong secrets.json của provider đã gỡ (key từ .env không xoá được)."""
    key = key_name(provider)
    secrets.delete(key)
    audit.log(actor, "settings.key.delete", key)


@router.put("/ai")
def put_ai(body: AiUpdate, actor: ActorDep) -> AiSettings:
    old = settings.load_ai()
    data = old.model_dump(mode="json", exclude_none=True)
    if body.providers is not None:
        bad = [n for n in body.providers if not PROVIDER_NAME.match(n)]
        if bad:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                [{"loc": ["providers", n], "msg": "use a-z, 0-9, _ or -"} for n in bad],
            )
        data["providers"] = body.providers
    if body.tasks is not None:
        data["tasks"] = body.tasks
    try:
        cfg = AiConfig.model_validate(data)
    except ValidationError as e:
        audit.log(actor, "settings.ai", None, {"error": "invalid"}, status="error")
        raise _invalid(e) from None
    settings.save_ai(cfg)
    audit.log(actor, "settings.ai", None, {"providers": list(cfg.providers)})
    for name in old.providers.keys() - cfg.providers.keys():
        _drop_key(name, actor)
    return _ai_view()


@router.delete("/ai/providers/{name}")
def delete_provider(name: str, actor: ActorDep) -> AiSettings:
    cfg = settings.load_ai()
    if name not in cfg.providers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "provider not found")
    used = [str(t) for t, routes in cfg.tasks.items() if any(r.provider == name for r in routes)]
    if used:
        raise HTTPException(status.HTTP_409_CONFLICT, f"provider is used by: {', '.join(used)}")
    data = cfg.model_dump(mode="json", exclude_none=True)
    del data["providers"][name]
    settings.save_ai(AiConfig.model_validate(data))
    audit.log(actor, "settings.ai.delete_provider", name)
    _drop_key(name, actor)
    return _ai_view()


def _provider_key(name: str) -> str:
    if name not in settings.load_ai().providers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "provider not found")
    return key_name(name)


@router.put("/ai/providers/{name}/key")
def put_ai_key(name: str, body: KeyBody, actor: ActorDep) -> KeyInfo:
    key = _provider_key(name)
    secrets.put(key, body.value)
    audit.log(actor, "settings.key.set", key)
    return secrets.info(key)


@router.delete("/ai/providers/{name}/key")
def delete_ai_key(name: str, actor: ActorDep) -> KeyInfo:
    key = _provider_key(name)
    secrets.delete(key)
    audit.log(actor, "settings.key.delete", key)
    return secrets.info(key)


class TestBody(BaseModel):
    model: str | None = None


@router.post("/ai/providers/{name}/test")
def test_provider(
    name: str, actor: ActorDep, body: Annotated[TestBody | None, Body()] = None
) -> TestResult:
    """Gọi thật một câu ngắn tới nhà cung cấp để kiểm tra key và model."""
    cfg = settings.load_ai()
    p = cfg.providers.get(name)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "provider not found")
    model = (body.model if body else None) or next(iter(p.models), None)
    provider = make_provider(name, p, secrets.all_keys())
    if model is None or model not in p.models:
        result = TestResult(ok=False, detail="unknown model")
    elif provider is None:
        result = TestResult(ok=False, detail="missing API key")
    else:
        schema = {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        }
        request = ProviderRequest(
            model,
            [{"role": "user", "content": 'Reply with the JSON object {"ok": true}.'}],
            schema,
            p.models[model].structured,
            None,
        )
        start = perf_counter()
        try:
            provider.complete(request)
            result = TestResult(ok=True, detail=f"{name}/{model} answered")
        except ProviderError as e:
            cause = e.__cause__
            result = TestResult(ok=False, detail=f"{e}: {cause}" if cause else str(e))
        result.latency_ms = int((perf_counter() - start) * 1000)
    audit.log(actor, "settings.ai.test", name, {"ok": result.ok})
    return result
