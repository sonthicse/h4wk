"""T12: toàn luồng collect → media → analyze với adapter giả, chạy Huey ở chế độ immediate."""

import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from h4wk.collectors import registry
from h4wk.collectors.base import Blocked, FetchResult
from h4wk.collectors.models import Cap, Normalized
from h4wk.jobs import queue

SAMPLE = (
    Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001/captures/20261118T160000"
)
VIDEO = "https://www.youtube.com/watch?v=h4wkDemo001"


class SampleCollector:
    """Nguồn giả trả về dữ liệu của bản thu mẫu T44."""

    name = "fake"
    capabilities = set(Cap)
    version = "fake-1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.n = Normalized.model_validate_json(
            (SAMPLE / "normalized.json").read_text(encoding="utf-8")
        )

    def fetch(self, cap: Cap, target, workdir: Path) -> FetchResult:  # noqa: ANN001
        if self.fail:
            raise Blocked("bị chặn")
        data = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            data["video"] = self.n.video
        elif cap == Cap.TRANSCRIPTS:
            data["transcripts"] = self.n.transcripts
        elif cap == Cap.COMMENTS:
            data["comments"] = self.n.comments
        elif cap == Cap.MEDIA:
            shutil.copy(SAMPLE / "sources/ytdlp/h4wkDemo001.mp4", workdir / "v.mp4")
            data["media"] = [{"kind": "video", "file": f"sources/{workdir.name}/v.mp4"}]
        return FetchResult(normalized=Normalized.model_validate(data))

    def health_check(self):  # noqa: ANN201
        raise NotImplementedError


@pytest.fixture
def fake_source(monkeypatch: pytest.MonkeyPatch) -> dict:
    holder = {"fail": False}
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: SampleCollector(holder["fail"])})
    return holder


@pytest.fixture(autouse=True)
def _immediate(data_dir: Path) -> Iterator[None]:
    queue.huey.immediate = True
    queue.huey_gpu.immediate = True
    yield
    for root, dirs, _ in os.walk(data_dir):
        for d in dirs:
            os.chmod(Path(root) / d, 0o755)


def _case(client: TestClient) -> str:
    case = client.post("/api/cases", json={"title": "Demo"}).json()
    r = client.post(
        f"/api/cases/{case['id']}/entities",
        json={"name": "Trần Văn Mẫu", "aliases": ["Mẫu Ca"], "abbreviations": ["TVM"]},
    )
    assert r.status_code == 201
    return case["id"]


def _lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_full_flow_ends_with_findings(client: TestClient, fake_source: dict) -> None:
    case_id = _case(client)
    r = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO})
    assert r.status_code == 202, r.text
    job = client.get(f"/api/jobs/{r.json()['id']}").json()
    assert job["status"] == "done", job
    assert job["progress"] == 100 and job["trigger"] == "user:thi"
    assert job["video_id"] == "h4wkDemo001" and job["capture"]
    assert [j["id"] for j in client.get(f"/api/jobs?case={case_id}").json()] == [job["id"]]
    findings = client.get(f"/api/cases/{case_id}/findings").json()
    assert findings, "phải có ít nhất một nghi vấn"
    assert {f["video_id"] for f in findings} == {"h4wkDemo001"}
    assert any("lừa đảo" in f["quote"] for f in findings)


def test_recent_capture_is_not_collected_again(client: TestClient, fake_source: dict) -> None:
    case_id = _case(client)
    first = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO}).json()
    second = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO}).json()
    j1 = client.get(f"/api/jobs/{first['id']}").json()
    j2 = client.get(f"/api/jobs/{second['id']}").json()
    assert j2["status"] == "done" and j2["capture"] == j1["capture"]
    forced = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO, "force": True})
    j3 = client.get(f"/api/jobs/{forced.json()['id']}").json()
    assert j3["capture"] != j1["capture"]


def test_failed_step_marks_job_failed_and_audits(
    client: TestClient, fake_source: dict, data_dir: Path
) -> None:
    case_id = _case(client)
    fake_source["fail"] = True
    r = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()['id']}").json()
    assert job["status"] == "failed" and job["error"]
    audit = _lines(data_dir / "cases" / case_id / "log" / "audit.jsonl")
    assert audit[-1]["action"] == "job.run" and audit[-1]["status"] == "error"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@VTV24",
        "https://www.youtube.com/playlist?list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG",
    ],
)
def test_channel_and_playlist_not_supported_yet(client: TestClient, url: str) -> None:
    case_id = _case(client)
    r = client.post(f"/api/cases/{case_id}/collect", json={"url": url})
    assert r.status_code == 400 and "chưa hỗ trợ" in r.json()["detail"]


def test_collect_unknown_case_404(client: TestClient) -> None:
    r = client.post("/api/cases/2026-11_case-9999/collect", json={"url": VIDEO})
    assert r.status_code == 404
