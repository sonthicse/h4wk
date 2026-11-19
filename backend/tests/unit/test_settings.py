"""T32: API Settings. Không response nào được chứa secret đầy đủ."""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from h4wk.ai import providers as ai_providers
from h4wk.ai.base import ProviderReply
from h4wk.ai.fake import FakeProvider
from h4wk.collectors.base import Health
from h4wk.collectors.models import Cap
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.providers import supadata
from h4wk.collectors.providers.supadata import CreditUsage, SupadataCollector
from h4wk.collectors.providers.youtube_api import YouTubeApiCollector
from h4wk.core.db import SourceStateRow, get_engine
from h4wk.core.types import VN_TZ

REPO_CONFIG = Path(__file__).parents[3] / "config"
YT_KEY = "AIzaSyTHISISAFULLSECRETKEY0001"
AI_KEY = "sk-ant-THISISAFULLSECRETKEY0002"


@pytest.fixture(autouse=True)
def _no_supadata_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(supadata, "credits_usage", lambda: None)


@pytest.fixture
def cfg(config_dir: Path) -> Path:
    for name in ("sources", "ai"):
        shutil.copy(REPO_CONFIG / f"{name}.toml.example", config_dir / f"{name}.toml")
    return config_dir


def test_no_response_contains_full_secret(
    client: TestClient, cfg, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(YouTubeApiCollector, "health_check", lambda self: Health(True, "ok"))
    bodies = [
        client.put("/api/settings/sources/youtube_api/key", json={"value": YT_KEY}),
        client.put("/api/settings/ai/providers/anthropic/key", json={"value": AI_KEY}),
        client.get("/api/settings/sources"),
        client.get("/api/settings/ai"),
        client.put("/api/settings/sources", json={}),
        client.put("/api/settings/ai", json={}),
        client.post("/api/settings/sources/youtube_api/test"),
        client.get("/api/events"),
        client.get("/openapi.json"),
    ]
    for r in bodies:
        assert r.status_code == 200, r.text
        assert YT_KEY not in r.text and AI_KEY not in r.text
    yt = next(s for s in bodies[2].json()["sources"] if s["name"] == "youtube_api")
    assert yt["key"] == {"set": True, "masked": "AIza…0001", "origin": "settings"}
    audit = client.app.state if False else None  # noqa: F841
    from h4wk.core.config import data_dir

    log = (data_dir() / "log" / "audit.jsonl").read_text(encoding="utf-8")
    assert YT_KEY not in log and AI_KEY not in log


def test_sources_show_youtube_quota_usage(client: TestClient, cfg) -> None:
    sources = {s["name"]: s for s in client.get("/api/settings/sources").json()["sources"]}
    yt = sources["youtube_api"]
    assert yt["implemented"] is True
    usage = yt["usage"]
    assert {k: usage[k] for k in ("used", "limit", "period")} == {
        "used": 0,
        "limit": 10000,
        "period": "day",
    }
    assert usage["resets_at"].endswith("+07:00")
    assert sources["ytdlp"]["usage"] is None


def test_sources_show_supadata_credits(
    client: TestClient, cfg, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(supadata, "credits_usage", lambda: CreditUsage(37, 100, "Free"))
    sources = {s["name"]: s for s in client.get("/api/settings/sources").json()["sources"]}
    assert sources["supadata"]["implemented"] is True
    assert sources["supadata"]["usage"] == {
        "used": 37,
        "limit": 100,
        "period": "month",
        "resets_at": None,
    }


def test_priority_change_is_used_by_next_job(client: TestClient, cfg) -> None:
    r = client.put("/api/settings/sources", json={"priority": {"video.metadata": ["ytdlp"]}})
    assert r.status_code == 200 and r.json()["priority"]["video.metadata"] == ["ytdlp"]
    from h4wk.core.config import data_dir

    orch = Orchestrator.from_config(root=data_dir())
    assert orch.settings.priority[Cap.VIDEO_METADATA][0] == "ytdlp"
    assert "# " not in (cfg / "sources.toml").read_text(encoding="utf-8")  # file đã ghi lại


def test_disabling_media_sources_reports_uncovered(client: TestClient, cfg) -> None:
    assert "video.media" not in client.get("/api/settings/sources").json()["uncovered"]
    r = client.put("/api/settings/sources", json={"sources": {"ytdlp": {"enabled": False}}})
    assert "video.media" in r.json()["uncovered"]


def test_paused_source_shows_error_and_resumes(client: TestClient, cfg) -> None:
    with Session(get_engine()) as s:
        s.add(
            SourceStateRow(
                provider="ytdlp",
                suspended_until=datetime.now(VN_TZ) + timedelta(minutes=10),
                last_error="Sign in to confirm you're not a bot",
                last_error_at=datetime.now(VN_TZ),
            )
        )
        s.commit()
    yt = next(
        x for x in client.get("/api/settings/sources").json()["sources"] if x["name"] == "ytdlp"
    )
    assert yt["status"] == "paused" and "not a bot" in yt["last_error"]
    assert yt["paused_until"].endswith("+07:00")
    r = client.post("/api/settings/sources/ytdlp/resume")
    assert r.json()["status"] == "active"


def test_source_tests(client: TestClient, cfg, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(SupadataCollector, "health_check", lambda self: Health(True, "ok"))
    assert client.post("/api/settings/sources/ytdlp/test").json()["ok"] is True
    assert client.post("/api/settings/sources/supadata/test").json()["ok"] is True
    assert client.put("/api/settings/sources/ytdlp/key", json={"value": "x"}).status_code == 400


def test_ai_replace_validate_delete(client: TestClient, cfg) -> None:
    ai = client.get("/api/settings/ai").json()
    tasks = ai["tasks"]
    bad = {**tasks, "media.vision": [{"provider": "glm", "model": "glm-4.7"}]}
    r = client.put("/api/settings/ai", json={"tasks": bad})
    assert r.status_code == 422 and isinstance(r.json()["detail"], list)
    assert "cannot read images" in json.dumps(r.json()["detail"])
    providers = {
        p["name"]: {k: p[k] for k in ("type", "base_url", "models")} for p in ai["providers"]
    }
    providers["local-llm"] = {
        "type": "openai_compat",
        "base_url": "http://localhost:8080/v1",
        "models": {"m1": {"vision": False, "structured": True}},
    }
    r = client.put("/api/settings/ai", json={"providers": providers})
    assert r.status_code == 200 and "local-llm" in {p["name"] for p in r.json()["providers"]}
    assert client.put("/api/settings/ai", json={"providers": {"Bad Name": {}}}).status_code == 422
    assert client.delete("/api/settings/ai/providers/anthropic").status_code == 409
    r = client.delete("/api/settings/ai/providers/local-llm")
    assert "local-llm" not in {p["name"] for p in r.json()["providers"]}


def test_ai_provider_test(client: TestClient, cfg, monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("h4wk.core.secrets.env_values", lambda: {})
    r = client.post("/api/settings/ai/providers/anthropic/test").json()
    assert r["ok"] is False and r["detail"] == "missing API key"
    client.put("/api/settings/ai/providers/anthropic/key", json={"value": AI_KEY})
    fake = FakeProvider([ProviderReply('{"ok": true}')])
    monkeypatch.setattr("h4wk.api.settings.make_provider", lambda *a: fake)
    r = client.post("/api/settings/ai/providers/anthropic/test", json={}).json()
    assert r["ok"] is True and r["latency_ms"] is not None
    assert ai_providers.key_name("local-llm") == "LOCAL_LLM_API_KEY"
