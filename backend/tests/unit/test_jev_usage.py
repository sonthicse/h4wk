"""T65: nhật ký request Jev, API usage và thử kết nối (Jev giả, không gọi mạng)."""

import io
import json
from datetime import datetime, timedelta
from urllib.error import HTTPError

import pytest
from _analysis_sample import ENTITY, _data
from fastapi.testclient import TestClient

from h4wk.analysis import jev, jev_log
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
    monkeypatch.setattr(jev, "CONCURRENCY", 1)
    return jev.classify(data.model_copy(update={"comments": []}), timeline, [ENTITY], [], "r_x")


def test_one_line_per_logical_request(data_dir, monkeypatch):
    http = lambda code: HTTPError(jev.URL, code, "", {"retry-after": "0"}, None)  # noqa: E731
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
    assert meta["requests"] == 2 and meta["kept"] == 1
    week = client.get("/api/settings/jev/usage?period=7d").json()
    assert week["requests"] == 4 and week["errors"] == 1
    assert week["recent_errors"][0]["status"] == "HTTP 500"
    assert week["recent_errors"][0]["source"] == "speech"
    month = client.get("/api/settings/jev/usage?period=30d").json()
    assert month["requests"] == 5
    assert "limit" not in month
    for key in ("since", "until"):
        assert datetime.fromisoformat(month[key]).utcoffset() == timedelta(hours=7)
    assert datetime.fromisoformat(week["recent_errors"][0]["at"]).utcoffset() == timedelta(hours=7)


def test_recent_errors_capped_at_five_newest_first(client: TestClient, data_dir):
    now = datetime.now(VN_TZ)
    _write(data_dir, [_row(now - timedelta(minutes=i), status=f"HTTP {500 + i}") for i in range(8)])
    errors = client.get("/api/settings/jev/usage?period=7d").json()["recent_errors"]
    assert [e["status"] for e in errors] == [f"HTTP {500 + i}" for i in range(5)]


def test_usage_empty_and_bad_period(client: TestClient, data_dir):
    body = client.get("/api/settings/jev/usage").json()
    assert body["requests"] == 0 and len(body["by_source"]) == 6
    assert body["input_tokens"] is None and body["output_tokens"] is None
    assert all(row["input_tokens"] is None for row in body["by_source"])
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
    usage = client.get("/api/settings/jev/usage").json()
    assert usage["requests"] == 2
    assert usage["by_source"][-1]["source"] == "connection_test"
    assert usage["recent_errors"][0]["video_id"] is None


def test_dashboard_has_jev_usage_field(client: TestClient, data_dir):
    assert client.get("/api/dashboard").json()["jev_usage"] is None


def test_month_start_uses_vietnam_time():
    utc_evening = datetime.fromisoformat("2026-10-31T18:00:00+00:00")
    assert jev_log.month_start(utc_evening).isoformat() == "2026-11-01T00:00:00+07:00"


@pytest.mark.parametrize("usage", [TEXT_MARK, {"input_tokens": True, "output_tokens": -1}])
def test_malformed_usage_records_null_tokens(data_dir, monkeypatch, usage):
    _run(monkeypatch, [{**_answer(), "usage": usage}, _answer()])
    first, second = _lines(data_dir)
    assert first["input_tokens"] is None and first["output_tokens"] is None
    assert second["input_tokens"] == 100
    assert TEXT_MARK not in json.dumps(first)


@pytest.mark.parametrize("reply", [None, {}, {"model": "test", "answers": {}}])
def test_connection_rejects_invalid_reply(client, data_dir, monkeypatch, reply):
    monkeypatch.setattr(jev.secrets, "get", lambda name: SECRET)
    monkeypatch.setattr(jev, "_call", lambda *args: reply)
    assert client.post("/api/settings/jev/test").json()["ok"] is False
    (row,) = _lines(data_dir)
    assert row["status"] == "error" and row["source_kind"] == "connection_test"
    assert all(row[k] is None for k in ("video_id", "capture", "run_id"))


def test_connection_retry_is_one_request(client, data_dir, monkeypatch):
    replies = iter([HTTPError(jev.URL, 429, "", {"retry-after": "0"}, None), _answer()])

    def urlopen(request, timeout):
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(json.dumps(reply).encode("utf-8"))

    monkeypatch.setattr(jev.secrets, "get", lambda name: SECRET)
    monkeypatch.setattr(jev.urllib.request, "urlopen", urlopen)
    assert client.post("/api/settings/jev/test").json()["ok"] is True
    (row,) = _lines(data_dir)
    assert row["retries_429"] == 1 and row["input_tokens"] == 100


def test_dashboard_month_counts_only_reported_tokens(client, data_dir, monkeypatch):
    now = datetime.fromisoformat("2026-11-01T00:01:00+07:00")

    class Clock(datetime):
        @classmethod
        def now(cls, tz):
            return now.astimezone(tz)

    monkeypatch.setattr("h4wk.api.dashboard.datetime", Clock)
    _write(
        data_dir,
        [
            {**_row(now - timedelta(minutes=2)), "input_tokens": 999},
            {**_row(now - timedelta(minutes=1)), "input_tokens": 0, "output_tokens": None},
            {**_row(now), "input_tokens": "invalid", "output_tokens": None},
            {**_row(now + timedelta(minutes=1)), "input_tokens": 999},
        ],
    )
    assert client.get("/api/dashboard").json()["jev_usage"] == {
        "requests": 2,
        "input_tokens": 0,
        "output_tokens": None,
    }
