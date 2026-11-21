"""T65: nhật ký request Jev, API usage và thử kết nối (Jev giả, không gọi mạng)."""

import io
import json
from datetime import datetime, timedelta
from urllib.error import HTTPError

from _analysis_sample import ENTITY, _data
from fastapi.testclient import TestClient

from h4wk.analysis import jev, jev_log
from h4wk.core.config_models import JevSettings
from h4wk.core.types import VN_TZ
from h4wk.media.timeline import FrameOcr, Segment

SECRET = "tsk-THISISAFULLSECRETKEY0003"
TEXT_MARK = "NOIDUNGBIMAT"


def _answer(noul=0.9):
    return {
        "model": "jev-test",
        "usage": {"input_tokens": 100, "output_tokens": 10},
        "answers": {
            "category": {"probabilities": {"insult": 0.8}},
            "is_attack": {"noul": noul},
            "target": {"choice": ENTITY.id},
            "severity": {"score": 1.0},
        },
    }


def _lines(data_dir):
    path = data_dir / "jev_calls.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def _run(monkeypatch, replies):
    """Chạy classify với `urlopen` giả trả lần lượt các phản hồi/ngoại lệ."""
    data, timeline = _data()
    data.video.title = TEXT_MARK
    data.video.description = ""
    data.comments = []
    timeline.thumbnails = []
    ocr = FrameOcr(text="Chữ trên ảnh", bbox=[0, 0, 1, 1], frame="f.jpg", t=0)
    timeline.segments = [Segment(id="seg_0001", start=0, end=1, ocr=[ocr])]
    replies = iter(replies)

    def urlopen(request, timeout):
        item = next(replies)
        if isinstance(item, Exception):
            raise item
        return io.BytesIO(json.dumps(item).encode("utf-8"))

    monkeypatch.setattr(jev.secrets, "get", lambda name: SECRET)
    monkeypatch.setattr(jev.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(jev.time, "sleep", lambda s: None)
    return jev.classify(
        data, timeline, [ENTITY], [], "r_x", JevSettings(concurrency=1), max_comments=0
    )


def test_one_line_per_logical_request(data_dir, monkeypatch):
    http = lambda code: HTTPError(jev.URL, code, "", {"retry-after": "0"}, None)  # noqa: E731
    # title: ok; đoạn có OCR: 429, 429 rồi ok.
    _run(monkeypatch, [_answer(), http(429), http(429), _answer(0.1)])
    rows = _lines(data_dir)
    sources = [r["source_kind"] for r in rows]
    assert sources.count("title") == 1
    title = next(r for r in rows if r["source_kind"] == "title")
    assert title["status"] == "ok" and title["kept"] is True and title["retries_429"] == 0
    assert (title["input_tokens"], title["output_tokens"]) == (100, 10)
    other = rows[1]
    assert other["status"] == "ok" and other["retries_429"] == 2 and other["kept"] is False
    assert [r["source_kind"] for r in rows] == ["title", "ocr"]
    assert datetime.fromisoformat(rows[0]["at"]).utcoffset() == timedelta(hours=7)


def test_error_line_keeps_status_only(data_dir, monkeypatch):
    _run(monkeypatch, [HTTPError(jev.URL, 500, "", {}, None) for _ in range(2)])
    rows = _lines(data_dir)
    assert rows and all(r["status"] == "HTTP 500" for r in rows)
    assert all(r["input_tokens"] is None for r in rows)


def test_log_never_contains_text_images_or_key(data_dir, monkeypatch):
    _run(monkeypatch, [_answer(), _answer()])
    text = (data_dir / "jev_calls.jsonl").read_text(encoding="utf-8")
    assert TEXT_MARK not in text and SECRET not in text and "base64" not in text
    assert set(json.loads(text.splitlines()[0])) == {
        "at",
        "video_id",
        "capture",
        "run_id",
        "source_kind",
        "images",
        "input_tokens",
        "output_tokens",
        "kept",
        "status",
        "retries_429",
    }


def _write(data_dir, rows):
    (data_dir / "jev_calls.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows) + "không phải json\n", encoding="utf-8"
    )


def _row(at, source="ocr", status="ok", **fields):
    return {
        "at": at.isoformat(),
        "video_id": "v1",
        "capture": "20261121T000000",
        "run_id": "r1",
        "source_kind": source,
        "images": 0,
        "input_tokens": 10,
        "output_tokens": 1,
        "kept": False,
        "status": status,
        "retries_429": 0,
    } | fields


def test_usage_api_periods_sources_and_errors(client: TestClient, data_dir):
    now = datetime.now(VN_TZ)
    rows = [
        _row(now, "title", kept=True),
        _row(now, "description", images=0),
        _row(now, "ocr", images=2, retries_429=3),
        _row(now - timedelta(days=3), "speech", status="HTTP 500"),
        _row(now - timedelta(days=20), "comment"),
        _row(now - timedelta(days=40), "comment"),
    ]
    _write(data_dir, rows)
    today = client.get("/api/settings/jev/usage?period=today").json()
    assert today["requests"] == 3 and today["image_requests"] == 1 and today["retries_429"] == 3
    assert today["kept"] == 1 and today["errors"] == 0 and today["input_tokens"] == 30
    assert [s["source"] for s in today["by_source"]] == list(
        ("speech", "ocr", "visual", "thumbnail", "comment", "metadata")
    )
    meta = next(s for s in today["by_source"] if s["source"] == "metadata")
    assert meta["requests"] == 2 and meta["kept"] == 1  # tiêu đề và mô tả gộp một dòng
    week = client.get("/api/settings/jev/usage?period=7d").json()
    assert week["requests"] == 4 and week["errors"] == 1
    assert week["recent_errors"][0]["status"] == "HTTP 500"
    assert week["recent_errors"][0]["source"] == "speech"
    month = client.get("/api/settings/jev/usage?period=30d").json()
    assert month["requests"] == 5  # dòng 40 ngày trước bị loại
    assert month["limit"] is None
    for key in ("since", "until"):
        assert datetime.fromisoformat(month[key]).utcoffset() == timedelta(hours=7)
    assert datetime.fromisoformat(week["recent_errors"][0]["at"]).utcoffset() == timedelta(hours=7)


def test_recent_errors_capped_at_five_newest_first(client: TestClient, data_dir):
    now = datetime.now(VN_TZ)
    _write(data_dir, [_row(now - timedelta(minutes=i), status=f"HTTP {500 + i}") for i in range(8)])
    errors = client.get("/api/settings/jev/usage?period=today").json()["recent_errors"]
    assert [e["status"] for e in errors] == [f"HTTP {500 + i}" for i in range(5)]


def test_usage_empty_and_bad_period(client: TestClient, data_dir):
    body = client.get("/api/settings/jev/usage").json()
    assert body["requests"] == 0 and len(body["by_source"]) == 6
    assert client.get("/api/settings/jev/usage?period=1y").status_code == 422


def test_connection_test_ok_error_and_no_key(client: TestClient, data_dir, monkeypatch):
    monkeypatch.setattr(jev.secrets, "get", lambda name: None)
    assert client.post("/api/settings/jev/test").json() == {
        "ok": False,
        "model": None,
        "latency_ms": None,
        "error": "TYPESAFE_API_KEY is not set",
    }
    monkeypatch.setattr(jev.secrets, "get", lambda name: SECRET)
    monkeypatch.setattr(jev, "_call", lambda key, state, questions, images=(): _answer())
    ok = client.post("/api/settings/jev/test").json()
    assert ok["ok"] is True and ok["model"] == "jev-test" and ok["latency_ms"] >= 0

    def fail(*args, **kwargs):
        raise RuntimeError(f"HTTP 401 {SECRET}")

    monkeypatch.setattr(jev, "_call", fail)
    bad = client.post("/api/settings/jev/test")
    assert bad.json()["ok"] is False and SECRET not in bad.text
    audit = (data_dir / "log" / "audit.jsonl").read_text(encoding="utf-8")
    assert "settings.jev.test" in audit and SECRET not in audit
    assert not (data_dir / "jev_calls.jsonl").exists()  # thử kết nối không tính vào usage


def test_dashboard_has_jev_usage_field(client: TestClient, data_dir):
    assert client.get("/api/dashboard").json()["jev_usage"] is None


def test_month_start_uses_vietnam_time():
    utc_evening = datetime.fromisoformat("2026-10-31T18:00:00+00:00")  # 01/11 01:00 giờ VN
    assert jev_log.month_start(utc_evening).isoformat() == "2026-11-01T00:00:00+07:00"
