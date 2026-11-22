import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

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
AI_KEY = "sk-jev-THISISAFULLSECRETKEY0002"


@pytest.fixture
def cfg(config_dir: Path) -> Path:
    for name in ("sources",):
        shutil.copy(REPO_CONFIG / f"{name}.toml.example", config_dir / f"{name}.toml")
    return config_dir


def test_no_response_contains_full_secret(
    client: TestClient, cfg, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(YouTubeApiCollector, "health_check", lambda self: Health(True, "ok"))
    bodies = [
        client.put("/api/settings/sources/youtube_api/key", json={"value": YT_KEY}),
        client.put("/api/settings/jev/key", json={"value": AI_KEY}),
        client.get("/api/settings/sources"),
        client.get("/api/settings/jev"),
        client.put("/api/settings/sources", json={}),
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
    assert "# " not in (cfg / "sources.toml").read_text(encoding="utf-8")


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


def test_ai_routes_are_gone(client: TestClient, cfg) -> None:
    assert client.get("/api/settings/ai").status_code == 404
    assert client.put("/api/settings/ai", json={}).status_code in (404, 405)


def _stored(data_dir: Path) -> dict:
    return json.loads((data_dir / "secrets.json").read_text(encoding="utf-8"))


def test_jev_key_lifecycle(client: TestClient, dotenv) -> None:
    dotenv.pop("TYPESAFE_API_KEY", None)
    assert client.get("/api/settings/jev").json()["key"]["set"] is False
    result = client.put("/api/settings/jev/key", json={"value": AI_KEY})
    assert result.status_code == 200
    assert AI_KEY not in result.text
    assert result.json()["origin"] == "settings"
    assert client.get("/api/settings/jev").json() == {"key": result.json()}
    assert client.delete("/api/settings/jev/key").json()["set"] is False


def test_watchlist_settings_roundtrip(client, config_dir) -> None:
    got = client.get("/api/settings/watchlist").json()
    assert got["threads_per_channel"] == 1 and got["initial_videos"] == 10
    r = client.put("/api/settings/watchlist", json={"threads_per_channel": 3, "initial_videos": 20})
    assert r.status_code == 200, r.text
    assert r.json()["threads_per_channel"] == 3 and r.json()["initial_videos"] == 20
    text = (config_dir / "sources.toml").read_text(encoding="utf-8")
    assert "threads_per_channel = 3" in text and "initial_videos = 20" in text
    assert client.put("/api/settings/watchlist", json={"threads_per_channel": 0}).status_code == 422
