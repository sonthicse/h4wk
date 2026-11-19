"""T46: link playlist tách thành mỗi video một job."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from h4wk.collectors import registry
from h4wk.collectors.base import Blocked, FetchResult
from h4wk.collectors.models import Cap, Normalized
from h4wk.jobs import pipeline

PLAYLIST = "https://www.youtube.com/playlist?list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG"
IDS = ["aaaaaaaaaaa", "bbbbbbbbbbb", "ccccccccccc"]


class PlaylistCollector:
    name = "fake"
    capabilities = {Cap.PLAYLIST_VIDEOS}
    version = "fake-1"
    ids = IDS + [IDS[0]]  # có một ID trùng
    error: Exception | None = None

    def fetch(self, cap, target, workdir: Path) -> FetchResult:  # noqa: ANN001
        if self.error:
            raise self.error
        return FetchResult(
            normalized=Normalized.model_validate(
                {"schema": "h4wk.normalized/1", "video_ids": self.ids}
            )
        )

    def health_check(self):  # noqa: ANN201
        raise NotImplementedError


@pytest.fixture
def source(monkeypatch: pytest.MonkeyPatch) -> PlaylistCollector:
    c = PlaylistCollector()
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: c})
    monkeypatch.setattr(pipeline, "start", lambda job_id: None)
    return c


def _audit(data_dir: Path) -> list[dict]:
    path = data_dir / "log" / "audit.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_playlist_makes_one_job_per_video(client: TestClient, source, data_dir: Path) -> None:
    r = client.post("/api/collect", json={"url": PLAYLIST})
    assert r.status_code == 202, r.text
    assert [j["video_id"] for j in r.json()] == IDS
    created = [a for a in _audit(data_dir) if a["action"] == "job.create"]
    assert len(created) == 3 and created[0]["detail"]["playlist"].startswith("PLx0")


def test_playlist_is_capped_by_config(client: TestClient, source, config_dir: Path) -> None:
    (config_dir / "sources.toml").write_text(
        "[collect]\nplaylist_max_videos = 2\n", encoding="utf-8"
    )
    r = client.post("/api/collect", json={"url": PLAYLIST})
    assert [j["video_id"] for j in r.json()] == IDS[:2]


def test_blocked_source_is_502_and_audited(client: TestClient, source, data_dir: Path) -> None:
    source.error = Blocked("bị chặn")
    r = client.post("/api/collect", json={"url": PLAYLIST})
    assert r.status_code == 502 and "could not list playlist videos" in r.json()["detail"]
    last = _audit(data_dir)[-1]
    assert last["action"] == "job.create" and last["status"] == "error"


def test_empty_playlist_is_400(client: TestClient, source) -> None:
    source.ids = []
    r = client.post("/api/collect", json={"url": PLAYLIST})
    assert r.status_code == 400 and r.json()["detail"] == "playlist has no videos"


def test_list_video_ids_writes_nothing(client: TestClient, source, data_dir: Path) -> None:
    before = {p.name for p in data_dir.iterdir()}
    assert pipeline.playlist_video_ids("PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG") == IDS
    assert {p.name for p in data_dir.iterdir()} == before
    assert not (data_dir / "playlists").exists() and not (data_dir / "videos").exists()


def test_single_video_still_returns_one_job(client: TestClient, source) -> None:
    r = client.post("/api/collect", json={"url": "https://www.youtube.com/watch?v=h4wkDemo001"})
    assert r.status_code == 202 and [j["video_id"] for j in r.json()] == ["h4wkDemo001"]
