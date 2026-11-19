"""T15: chuyển response của Supadata sang dữ liệu chung và gọi adapter qua MockTransport."""

import json
from pathlib import Path

import pytest

from h4wk.collectors.base import Blocked, NotFound, QuotaExceeded, Transient, Unsupported
from h4wk.collectors.models import Cap, TranscriptKind
from h4wk.collectors.providers import supadata as s
from h4wk.collectors.targets import Target, TargetKind

RAW = Path(__file__).resolve().parents[1] / "fixtures" / "raw" / "supadata"
VIDEO = Target(TargetKind.VIDEO, "h4wkDemo001")
CHANNEL = Target(TargetKind.CHANNEL, "UCh4wkDemoChannel000000")


def raw(name: str) -> dict:
    return json.loads((RAW / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    s._me_cache.clear()


def test_video_and_channel() -> None:
    d = raw("video.json")
    v = s.video_from_supadata(d)
    assert (v.id, v.channel_id, v.title) == (
        "h4wkDemo001",
        "UCh4wkDemoChannel000000",
        "Video thử nghiệm h4wk",
    )
    assert v.duration_s == 40 and v.view_count == 12 and v.like_count is None
    assert v.tags == ["thử nghiệm", "h4wk"]
    assert v.published_at.utcoffset().total_seconds() == 7 * 3600
    c = s.channel_from_supadata(d)
    assert (c.id, c.title) == ("UCh4wkDemoChannel000000", "Kênh thử nghiệm h4wk")


def test_transcript_conversion() -> None:
    t = s.transcript_from_supadata(raw("transcript_native_vi.json"))
    assert t.kind == TranscriptKind.SUPADATA_AI and t.lang == "vi"
    assert [(g.start, g.end, g.text) for g in t.segments] == [
        (0.0, 2.0, "Xin chào các bạn"),  # end bị kẹp theo đoạn kế (chồng thời gian)
        (2.0, 5.0, "đây là video thử nghiệm"),
        (8.0, 10.0, "Cảm ơn đã xem"),  # đoạn rỗng bị bỏ
    ]


@pytest.mark.parametrize(
    ("status", "body", "kind"),
    [
        (206, raw("error_unavailable.json"), Unsupported),
        (404, raw("error_not_found.json"), NotFound),
        (429, raw("error_limit.json"), QuotaExceeded),
        (401, raw("error_unauthorized.json"), Blocked),
        (402, {"error": "upgrade-required", "message": "x"}, Blocked),
        (502, {"error": "upstream-error", "message": "x"}, Transient),
        (500, {"error": "internal-error", "message": "x"}, Transient),
        (503, None, Transient),
    ],
)
def test_classify_error(status: int, body: dict | None, kind: type) -> None:
    err = s.classify_error(status, body)
    assert type(err) is kind and f"Supadata {status}" in str(err)


def test_video_metadata(supadata_api, tmp_path: Path) -> None:
    res = supadata_api.collector().fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    assert res.normalized.video.id == "h4wkDemo001" and res.normalized.channel.title
    assert res.cost.credits == 0 and (tmp_path / "h4wkDemo001.video.json").exists()


def test_transcript_native(supadata_api, tmp_path: Path) -> None:
    res = supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    (req,) = supadata_api.requests
    assert req.url.params["mode"] == "native" and req.url.params["lang"] == "vi"
    assert req.headers["x-api-key"] == "test-key" and "test-key" not in str(req.url)
    assert res.cost.credits == 1
    assert res.normalized.transcripts[0].kind == TranscriptKind.SUPADATA_AI
    assert (tmp_path / "h4wkDemo001.transcript.native.json").exists()


def test_native_other_language_falls_back_to_generate_job(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(200, raw("transcript_native_en.json"))]
    supadata_api.override["generate"] = [(202, raw("transcript_job.json"))]
    supadata_api.override["job"] = [(200, raw("job_active.json")), (200, raw("job_completed.json"))]
    res = supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    assert supadata_api.sleeps == [1.0, 1.0]
    t = res.normalized.transcripts[0]
    assert t.lang == "vi" and t.segments[0].text == "Đây là bản AI tạo"
    assert res.cost.credits == 3
    assert (tmp_path / "h4wkDemo001.transcript.generate.json").exists()


def test_native_unavailable_then_generate_immediately(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(200, raw("job_completed.json"))]
    res = supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    assert res.cost.credits == 3 and supadata_api.sleeps == []


def test_job_failed_is_blocked(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(202, raw("transcript_job.json"))]
    supadata_api.override["job"] = [(200, raw("job_failed.json"))]
    with pytest.raises(Blocked, match="upstream down"):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)


def test_job_timeout_is_blocked(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(202, raw("transcript_job.json"))]
    supadata_api.override["job"] = [(200, raw("job_active.json"))]
    with pytest.raises(Blocked, match="did not finish within 600 s"):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    assert len(supadata_api.sleeps) == 601


def test_generate_without_speech_is_unsupported(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(200, {"content": [], "lang": "vi"})]
    with pytest.raises(Unsupported, match="no speech"):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)


def test_errors(supadata_api, tmp_path: Path) -> None:
    with pytest.raises(Blocked, match="SUPADATA_API_KEY is not set"):
        supadata_api.collector(key=lambda: None).fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    supadata_api.override["video"] = [(404, raw("error_not_found.json"))]
    with pytest.raises(NotFound):
        supadata_api.collector().fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    supadata_api.override["video"] = [(429, raw("error_limit.json"))]
    with pytest.raises(QuotaExceeded):
        supadata_api.collector().fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    with pytest.raises(Unsupported):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, CHANNEL, tmp_path)


def test_credits_usage_cached(supadata_api) -> None:
    c = supadata_api.collector()
    assert s.credits_usage(c) == s.CreditUsage(37, 100, "Free")
    assert s.credits_usage(c) == s.CreditUsage(37, 100, "Free")
    assert len(supadata_api.requests) == 1


def test_credits_usage_none_on_error_or_no_key(supadata_api) -> None:
    supadata_api.override["me"] = [(500, {"error": "internal-error", "message": "x"})]
    assert s.credits_usage(supadata_api.collector()) is None
    assert s.credits_usage(supadata_api.collector()) is None  # lỗi cũng được nhớ
    assert len(supadata_api.requests) == 1
    s._me_cache.clear()
    assert s.credits_usage(supadata_api.collector(key=lambda: None)) is None


def test_health_check(supadata_api) -> None:
    h = supadata_api.collector().health_check()
    assert h.ok and "37/100" in h.detail
    assert supadata_api.collector(key=lambda: None).health_check().ok is False


def test_202_without_job_id_is_blocked(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(202, {})]
    with pytest.raises(Blocked, match="without jobId"):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)


def test_poll_survives_transient_error_without_new_job(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(202, raw("transcript_job.json"))]
    supadata_api.override["job"] = [
        (503, {"error": "upstream-error", "message": "x"}),
        (200, raw("job_completed.json")),
    ]
    res = supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    assert res.normalized.transcripts[0].segments
    modes = [r.url.params.get("mode") for r in supadata_api.requests]
    assert modes.count("generate") == 1


def test_generate_server_error_is_blocked_and_not_retried(supadata_api, tmp_path: Path) -> None:
    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    supadata_api.override["generate"] = [(503, {"error": "upstream-error", "message": "x"})]
    with pytest.raises(Blocked, match="not retried"):
        supadata_api.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    modes = [r.url.params.get("mode") for r in supadata_api.requests]
    assert modes.count("generate") == 1


def test_generate_timeout_is_blocked(supadata_api, tmp_path: Path) -> None:
    import httpx2

    def handler(request):  # noqa: ANN001, ANN202
        if request.url.params.get("mode") == "generate":
            raise httpx2.ReadTimeout("slow", request=request)
        return supadata_api.handler(request)

    supadata_api.override["native"] = [(206, raw("error_unavailable.json"))]
    c = supadata_api.collector()
    c.client = httpx2.Client(transport=httpx2.MockTransport(handler))
    with pytest.raises(Blocked, match="not retried"):
        c.fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
