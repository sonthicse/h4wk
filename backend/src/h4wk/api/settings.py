"""API Settings (T32): nguồn thu, nhà cung cấp AI, API key. Key chỉ gửi lên; response chỉ
có bản che. Mọi thao tác ghi có audit nhưng không ghi giá trị key."""

import re
from datetime import datetime
from time import perf_counter
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from sqlmodel import Session

from h4wk.api.deps import current_actor
from h4wk.collectors import quota, registry
from h4wk.collectors.models import Cap
from h4wk.collectors.orchestrator import Settings as RouteSettings
from h4wk.collectors.providers import supadata
from h4wk.core import audit, secrets, settings
from h4wk.core.config_models import SourcesConfig
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


class JevSettingsView(BaseModel):
    key: KeyInfo


_JEV_KEY = "TYPESAFE_API_KEY"


@router.get("/jev")
def get_jev() -> JevSettingsView:
    return JevSettingsView(key=secrets.info(_JEV_KEY))


@router.put("/jev/key")
def put_jev_key(body: KeyBody, actor: ActorDep) -> KeyInfo:
    secrets.put(_JEV_KEY, body.value)
    audit.log(actor, "settings.key.set", _JEV_KEY)
    return secrets.info(_JEV_KEY)


@router.delete("/jev/key")
def delete_jev_key(actor: ActorDep) -> KeyInfo:
    secrets.delete(_JEV_KEY)
    audit.log(actor, "settings.key.delete", _JEV_KEY)
    return secrets.info(_JEV_KEY)
