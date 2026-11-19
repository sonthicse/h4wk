"""T12: toàn luồng collect → media → analyze với adapter giả, chạy Huey ở chế độ immediate."""

import json
import os
import shutil
from collections.abc import Iterator
from itertools import repeat
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from h4wk.ai.base import ProviderReply
from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.fake import FakeProvider
from h4wk.ai.gateway import AIGateway
from h4wk.collectors import registry
from h4wk.collectors.base import Blocked, FetchResult
from h4wk.collectors.models import Cap, Normalized
from h4wk.jobs import pipeline, queue
from h4wk.media import ocr, stt, vision
from h4wk.media.timeline import Timeline

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
        elif cap == Cap.THUMBNAILS:
            shutil.copy(SAMPLE / "sources/ytdlp/maxres.jpg", workdir / "maxres.jpg")
            data["thumbnails"] = [
                {
                    "name": "maxres",
                    "file": f"sources/{workdir.name}/maxres.jpg",
                    "url": "https://example.com/t.jpg",
                }
            ]
        elif cap == Cap.MEDIA:
            shutil.copy(SAMPLE / "sources/ytdlp/h4wkDemo001.mp4", workdir / "v.mp4")
            data["media"] = [{"kind": "video", "file": f"sources/{workdir.name}/v.mp4"}]
        return FetchResult(normalized=Normalized.model_validate(data))

    def health_check(self):  # noqa: ANN201
        raise NotImplementedError


@pytest.fixture
def fake_source(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> dict:
    holder = {"fail": False}
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: SampleCollector(holder["fail"])})
    if request.node.get_closest_marker("gpu"):
        model = os.getenv("H4WK_STT_MODEL")
        if not model:
            pytest.skip("Cần H4WK_STT_MODEL để kiểm tra worker GPU")
    else:
        model = "test"
        monkeypatch.setattr(
            stt, "_load_model", lambda _: SimpleNamespace(transcribe=lambda *a, **kw: ([], None))
        )
    monkeypatch.setattr(pipeline, "_stt_worker", stt.SttWorker(model))
    monkeypatch.setattr(
        ocr,
        "_recognize",
        lambda paths: [[{"text": "Chữ", "bbox": [0, 0, 1, 1], "score": 1}] for _ in paths],
    )
    provider = FakeProvider(repeat(ProviderReply('{"description":"Ảnh mẫu","offensive_cues":[]}')))
    gateway = AIGateway(
        {"anthropic": provider},
        config_path=AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=data_dir,
    )
    monkeypatch.setattr(vision, "AIGateway", lambda: gateway)
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


def test_full_flow_ends_with_findings(
    client: TestClient, data_dir: Path, fake_source: dict
) -> None:
    case_id = _case(client)
    r = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO})
    assert r.status_code == 202, r.text
    job = client.get(f"/api/jobs/{r.json()['id']}").json()
    assert job["status"] == "done", job["error"]
    assert job["progress"] == 100 and job["trigger"] == "user:thi"
    assert job["video_id"] == "h4wkDemo001" and job["capture"]
    assert [j["id"] for j in client.get(f"/api/jobs?case={case_id}").json()] == [job["id"]]
    findings = client.get(f"/api/cases/{case_id}/findings").json()
    assert findings, "phải có ít nhất một nghi vấn"
    assert {f["video_id"] for f in findings} == {"h4wkDemo001"}
    assert any("lừa đảo" in f["quote"] for f in findings)
    derived = data_dir / "cases" / case_id / "videos" / job["video_id"] / "derived" / job["capture"]
    timeline = Timeline.model_validate_json((derived / "timeline.json").read_bytes())
    manifest = json.loads(
        (derived.parents[1] / "captures" / job["capture"] / "manifest.json").read_bytes()
    )
    assert timeline.source_video_sha256 == manifest["files"]["sources/fake/v.mp4"]["sha256"]
    frames = json.loads((derived / "frames/index.json").read_bytes())["frames"]
    expected = {f["file"] for f in frames}
    assert {v.frame for seg in timeline.segments for v in seg.visual} == expected
    assert {v.frame for seg in timeline.segments for v in seg.ocr} == expected
    vision_rows = json.loads((derived / "vision.json").read_bytes())
    assert set(vision_rows) == expected | {"sources/fake/maxres.jpg"}
    assert any(seg.speech for seg in timeline.segments)
    assert any(seg.visual and seg.ocr for seg in timeline.segments)
    assert timeline.thumbnails[0].visual.provider == "anthropic"
    assert timeline.thumbnails[0].ocr[0].text == "Chữ"


def test_text_after_metadata_processes_only_thumbnails(client, fake_source, data_dir):
    case_id = _case(client)
    for level in ["metadata", "text"]:
        response = client.post(
            f"/api/cases/{case_id}/collect", json={"url": VIDEO, "level": level}
        ).json()
        job = client.get(f"/api/jobs/{response['id']}").json()
        assert job["status"] == "done", job["error"]
        derived = (
            data_dir / "cases" / case_id / "videos" / job["video_id"] / "derived" / job["capture"]
        )
        timeline = Timeline.model_validate_json((derived / "timeline.json").read_bytes())
        assert timeline.source_video_sha256 is None
        assert not (derived / "proxy_480p.mp4").exists()
        if level == "metadata":
            assert not timeline.thumbnails and not (derived / "vision.json").exists()
        else:
            assert timeline.thumbnails[0].visual and timeline.thumbnails[0].ocr
            assert any(segment.speech for segment in timeline.segments)


@pytest.mark.parametrize(
    "fake_source",
    [
        pytest.param(None, id="offline"),
        pytest.param(None, marks=pytest.mark.gpu, id="gpu"),
    ],
    indirect=True,
)
def test_recent_capture_is_not_collected_again(
    client: TestClient, fake_source: dict, data_dir: Path, caplog
) -> None:
    caplog.set_level("INFO", logger=stt.__name__)
    case_id = _case(client)
    first = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO}).json()
    initial_calls = (data_dir / "ai_calls.jsonl").read_bytes()
    second = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO}).json()
    j1 = client.get(f"/api/jobs/{first['id']}").json()
    j2 = client.get(f"/api/jobs/{second['id']}").json()
    assert j2["status"] == "done" and j2["capture"] == j1["capture"]
    assert (data_dir / "ai_calls.jsonl").read_bytes() == initial_calls
    forced = client.post(f"/api/cases/{case_id}/collect", json={"url": VIDEO, "force": True})
    j3 = client.get(f"/api/jobs/{forced.json()['id']}").json()
    assert j3["status"] == "done", j3["error"]
    assert j3["capture"] != j1["capture"]
    assert sum("Đã nạp model STT" in record.getMessage() for record in caplog.records) == 1


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
