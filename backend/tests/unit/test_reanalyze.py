import shutil

import pytest
from _analysis_sample import SAMPLE
from fastapi.testclient import TestClient

from h4wk.jobs import pipeline
from h4wk.jobs.queue import huey


@pytest.fixture
def video(data_dir, monkeypatch):
    shutil.copytree(SAMPLE, data_dir / "videos" / "h4wkDemo001")
    (data_dir / "videos" / "noTimeline1").mkdir()
    monkeypatch.setattr(huey, "immediate", True)
    return data_dir / "videos" / "h4wkDemo001"


def _runs(video):
    return sorted(p.name for p in video.glob("derived/*/analysis/*") if p.is_dir())


def test_reanalyze_all_creates_new_run(client: TestClient, video) -> None:
    before = _runs(video)
    r = client.post("/api/reanalyze", json={})
    assert r.status_code == 202, r.text
    [job] = r.json()
    assert job["video_id"] == "h4wkDemo001"
    done = client.get(f"/api/jobs/{job['id']}").json()
    assert done["status"] == "done" and done["run_id"] not in before
    assert done["run_id"] in _runs(video)


def test_reanalyze_one_video_without_timeline_is_409(client: TestClient, video) -> None:
    r = client.post("/api/reanalyze", json={"video_ids": ["noTimeline1"]})
    assert r.status_code == 409
    assert client.post("/api/reanalyze", json={"video_ids": ["../x"]}).status_code == 400


def test_reanalyze_quota_keeps_old_run(client: TestClient, video, monkeypatch) -> None:
    before = _runs(video)
    monkeypatch.setattr(pipeline.runner, "analyze", lambda *a, **k: ([], [], "HTTP 429"))
    [job] = client.post("/api/reanalyze", json={"video_ids": ["h4wkDemo001"]}).json()
    got = client.get(f"/api/jobs/{job['id']}").json()
    assert got["status"] == "failed" and "429" in got["error"]
    assert _runs(video) == before
