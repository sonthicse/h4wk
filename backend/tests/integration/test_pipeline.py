"""T12: toàn luồng collect → media → analyze với adapter giả, chạy Huey ở chế độ immediate."""
# ruff: noqa: F811

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pipeline_fixtures import VIDEO, SampleCollector, _immediate, fake_source  # noqa: F401

from h4wk.collectors import registry
from h4wk.media import stt
from h4wk.media.timeline import Timeline


def _entity(client: TestClient) -> None:
    r = client.post(
        "/api/entities",
        json={"name": "Trần Văn Mẫu", "aliases": ["Mẫu Ca"], "abbreviations": ["TVM"]},
    )
    assert r.status_code == 201


def _lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def _vision_calls(data_dir: Path) -> list[dict]:
    rows = _lines(data_dir / "ai_calls.jsonl")
    return [r for r in rows if r["task"] == "media.vision"]


def test_full_flow_ends_with_findings(
    client: TestClient, data_dir: Path, fake_source: dict
) -> None:
    _entity(client)
    r = client.post("/api/collect", json={"url": VIDEO})
    assert r.status_code == 202, r.text
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    assert job["progress"] == 100 and job["trigger"] == "user:thi"
    assert job["video_id"] == "h4wkDemo001" and job["capture"]
    assert [j["id"] for j in client.get("/api/jobs").json()] == [job["id"]]
    findings = client.get("/api/findings").json()
    assert findings, "phải có ít nhất một nghi vấn"
    assert {f["video_id"] for f in findings} == {"h4wkDemo001"}
    assert any("lừa đảo" in f["quote"] for f in findings)
    derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
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
    _entity(client)
    for level in ["metadata", "text"]:
        response = client.post("/api/collect", json={"url": VIDEO, "level": level}).json()[0]
        job = client.get(f"/api/jobs/{response['id']}").json()
        assert job["status"] == "done", job["error"]
        derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
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
    _entity(client)
    first = client.post("/api/collect", json={"url": VIDEO}).json()[0]
    initial_calls = _vision_calls(data_dir)
    second = client.post("/api/collect", json={"url": VIDEO}).json()[0]
    j1 = client.get(f"/api/jobs/{first['id']}").json()
    j2 = client.get(f"/api/jobs/{second['id']}").json()
    assert j2["status"] == "done" and j2["capture"] == j1["capture"]
    # Chạy lại chỉ phân tích lại (analysis.classify); media.vision không được gọi thêm.
    assert _vision_calls(data_dir) == initial_calls
    forced = client.post("/api/collect", json={"url": VIDEO, "force": True})
    j3 = client.get(f"/api/jobs/{forced.json()[0]['id']}").json()
    assert j3["status"] == "done", j3["error"]
    assert j3["capture"] != j1["capture"]
    assert sum("Đã nạp model STT" in record.getMessage() for record in caplog.records) == 1


def test_failed_step_marks_job_failed_and_audits(
    client: TestClient, fake_source: dict, data_dir: Path
) -> None:
    _entity(client)
    fake_source["fail"] = True
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "failed" and job["error"]
    audit = _lines(data_dir / "log" / "audit.jsonl")
    assert audit[-1]["action"] == "job.run" and audit[-1]["status"] == "error"


def test_llm_failure_keeps_job_done(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from itertools import repeat

    from h4wk.ai.base import ProviderReply
    from h4wk.ai.config import AI_CONFIG_PATH
    from h4wk.ai.fake import FakeProvider
    from h4wk.ai.gateway import AIGateway
    from h4wk.jobs import pipeline

    broken = AIGateway(
        {"anthropic": FakeProvider(repeat(ProviderReply("not json")))},
        config_path=AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=data_dir,
    )
    monkeypatch.setattr(pipeline, "AIGateway", lambda: broken)
    _entity(client)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done" and job["error"] is None
    assert client.get("/api/findings").json(), "nghi vấn tĩnh vẫn còn"
    done = next(e for e in client.get("/api/events").json() if e["kind"] == "job_done")
    assert "LLM analysis skipped" in done["message"]
    run = _lines(data_dir / "log" / "audit.jsonl")[-1]
    assert run["action"] == "job.run" and "llm_error" in json.dumps(run)


def test_vision_failure_for_one_image_keeps_job_done(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.ai.base import ProviderError, ProviderReply
    from h4wk.ai.config import AI_CONFIG_PATH
    from h4wk.ai.gateway import AIGateway
    from h4wk.media import vision

    class OneBad:
        bad = None

        def complete(self, request):  # noqa: ANN001, ANN201
            if self.bad is None:
                self.bad = request.image
            if request.image == self.bad:
                raise ProviderError("boom")
            return ProviderReply('{"description":"Ảnh mẫu","offensive_cues":[]}')

    gateway = AIGateway(
        {"anthropic": OneBad()},
        config_path=AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=data_dir,
    )
    monkeypatch.setattr(vision, "AIGateway", lambda: gateway)
    _entity(client)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    done = next(e for e in client.get("/api/events").json() if e["kind"] == "job_done")
    assert "could not be described" in done["message"]
    derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
    timeline = Timeline.model_validate_json((derived / "timeline.json").read_bytes())
    described = {v.frame for seg in timeline.segments for v in seg.visual}
    cached = set(json.loads((derived / "vision.json").read_bytes()))
    assert cached == described | {t.file for t in timeline.thumbnails if t.visual}
    audit = [r for r in _lines(data_dir / "log" / "audit.jsonl") if r["action"] == "media.vision"]
    assert audit and audit[0]["status"] == "error"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/@VTV24",
    ],
)
def test_channel_is_not_supported_here(client: TestClient, url: str) -> None:
    _entity(client)
    r = client.post("/api/collect", json={"url": url})
    assert r.status_code == 400 and "not supported" in r.json()["detail"]


def test_ytdlp_disabled_still_collects_text(
    client: TestClient,
    fake_source: dict,
    data_dir: Path,
    config_dir: Path,
    ytapi,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (config_dir / "sources.toml").write_text("[sources.ytdlp]\nenabled = false\n", encoding="utf-8")
    monkeypatch.setattr(
        registry,
        "COLLECTORS",
        {"ytdlp": lambda: SampleCollector(), "youtube_api": ytapi.collector},
    )
    _entity(client)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    cap = data_dir / "videos" / "h4wkDemo001" / "captures" / job["capture"]
    sources = json.loads((cap / "manifest.json").read_bytes())["sources"]
    by_what = {}
    for s in sources:
        by_what.setdefault(s["what"], []).append(s)
    assert all(s["status"] == "disabled" for s in sources if s["provider"] == "ytdlp")
    assert [(s["provider"], s["status"]) for s in by_what["video.media"]] == [
        ("ytdlp", "disabled"),
        (None, "no_source"),
    ]
    expected = {"video.metadata": 2, "video.comments": 3, "video.thumbnails": 0}
    for what in expected:
        ok = [s for s in by_what[what] if s["status"] == "ok"]
        assert [s["provider"] for s in ok] == ["youtube_api"], what
        # thumbnails dùng lại video đã lấy ở bước metadata nên không tốn thêm quota
        assert ok[0]["cost"]["quota_units"] == expected[what], what
    normalized = json.loads((cap / "normalized.json").read_bytes())
    assert normalized["video"]["id"] == "h4wkDemo001" and normalized["media"] == []
    assert normalized["comments"] and any(t["name"] == "maxres" for t in normalized["thumbnails"])


class _SameVectorEmbedder:
    """Mọi ô cắt đều trùng ảnh mẫu (cosine 1), dùng để kiểm luồng mà không cần model."""

    name = "same"

    def embed(self, images):  # noqa: ANN001, ANN201
        import numpy as np

        return np.ones((len(images), 4)) / 2.0


def _add_ref_image(data_dir: Path, entity_id: str = "e_01") -> None:
    import shutil

    folder = data_dir / "entities" / entity_id / "refs" / "image"
    folder.mkdir(parents=True)
    ref = Path(__file__).resolve().parents[1] / "fixtures/refs/e_01/image/ref_01.png"
    shutil.copyfile(ref, folder / "0123456789abcdef.png")


def test_ref_image_hits_reach_hits_json(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.jobs import pipeline

    monkeypatch.setattr(pipeline, "_ref_embedder", _SameVectorEmbedder())
    _entity(client)
    _add_ref_image(data_dir)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
    ref_hits = json.loads((derived / "ref_hits.json").read_text(encoding="utf-8"))
    assert ref_hits and {h["via"] for h in ref_hits} == {"ref_image"}
    assert (derived / "embeddings.npz").is_file()
    run = next((derived / "analysis").iterdir())
    hits = json.loads((run / "hits.json").read_text(encoding="utf-8"))
    assert {h["frame"] for h in hits if h["via"] == "ref_image"} == {h["frame"] for h in ref_hits}


def test_ref_image_disabled_skips_matching(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.core.config import config_dir
    from h4wk.jobs import pipeline

    class Boom:
        name = "boom"

        def embed(self, images):  # noqa: ANN001, ANN201
            raise AssertionError("không được gọi")

    monkeypatch.setattr(pipeline, "_ref_embedder", Boom())
    (config_dir() / "analysis.toml").write_text("[ref_image]\nenabled = false\n", encoding="utf-8")
    _entity(client)
    _add_ref_image(data_dir)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
    assert not (derived / "ref_hits.json").exists()


def test_missing_torch_skips_matching_and_job_is_done(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.jobs import pipeline

    class NoTorch:
        name = "no-torch"

        def embed(self, images):  # noqa: ANN001, ANN201
            raise ImportError("No module named 'torch'")

    monkeypatch.setattr(pipeline, "_ref_embedder", NoTorch())
    _entity(client)
    _add_ref_image(data_dir)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    rows = [x for x in _lines(data_dir / "log" / "audit.jsonl") if x["action"] == "media.match"]
    assert rows and rows[0]["detail"]["skipped"] == "torch not installed"


def test_stale_ref_hits_are_removed_when_matching_is_skipped(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.core.config import config_dir
    from h4wk.jobs import pipeline

    monkeypatch.setattr(pipeline, "_ref_embedder", _SameVectorEmbedder())
    _entity(client)
    _add_ref_image(data_dir)
    first = client.post("/api/collect", json={"url": VIDEO}).json()[0]
    j1 = client.get(f"/api/jobs/{first['id']}").json()
    derived = data_dir / "videos" / j1["video_id"] / "derived" / j1["capture"]
    assert (derived / "ref_hits.json").exists()
    (config_dir() / "analysis.toml").write_text("[ref_image]\nenabled = false\n", encoding="utf-8")
    second = client.post("/api/collect", json={"url": VIDEO}).json()[0]  # cùng bản thu
    j2 = client.get(f"/api/jobs/{second['id']}").json()
    assert j2["status"] == "done" and j2["capture"] == j1["capture"]
    assert not (derived / "ref_hits.json").exists()
    latest = max((derived / "analysis").iterdir(), key=lambda p: p.name)
    hits = json.loads((latest / "hits.json").read_text(encoding="utf-8"))
    assert all(h["via"] != "ref_image" for h in hits)


def test_match_error_is_audited_and_job_is_done(
    client: TestClient, fake_source: dict, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from h4wk.jobs import pipeline

    class Broken:
        name = "broken"

        def embed(self, images):  # noqa: ANN001, ANN201
            raise RuntimeError("CUDA out of memory")

    monkeypatch.setattr(pipeline, "_ref_embedder", Broken())
    _entity(client)
    _add_ref_image(data_dir)
    r = client.post("/api/collect", json={"url": VIDEO})
    job = client.get(f"/api/jobs/{r.json()[0]['id']}").json()
    assert job["status"] == "done", job["error"]
    derived = data_dir / "videos" / job["video_id"] / "derived" / job["capture"]
    assert not (derived / "ref_hits.json").exists()
    rows = [x for x in _lines(data_dir / "log" / "audit.jsonl") if x["action"] == "media.match"]
    assert rows and rows[0]["status"] == "error" and "out of memory" in rows[0]["detail"]["error"]
