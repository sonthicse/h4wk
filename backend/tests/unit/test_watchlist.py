"""T30: watchlist với RSS giả và nguồn kênh giả; job chỉ được ghi nhận, không chạy."""

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from h4wk.collectors import registry
from h4wk.collectors.base import FetchResult
from h4wk.collectors.models import Cap, Normalized
from h4wk.core.types import VN_TZ
from h4wk.jobs import pipeline
from h4wk.watchlist import rss, service

CHANNEL = "UCJDyIKGZ9zpTKDTEXpivGZw"
FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
 <entry><yt:videoId>vidAAAAAAA1</yt:videoId><title>Tin mới</title>
  <published>2026-11-19T01:00:00+00:00</published></entry>
 <entry><yt:videoId>vidAAAAAAA0</yt:videoId><title>Tin cũ</title>
  <published>2026-11-18T01:00:00+00:00</published></entry>
</feed>""".encode()


def _vid(i: int) -> str:
    return f"vid{i:08d}"


class ChannelCollector:
    name = "fake"
    capabilities = {Cap.CHANNEL_METADATA, Cap.CHANNEL_VIDEOS}
    version = "fake-1"

    def __init__(self, ids: list[str]) -> None:
        self.ids = ids

    def fetch(self, cap: Cap, target, workdir: Path) -> FetchResult:  # noqa: ANN001
        data: dict = {"schema": "h4wk.normalized/1"}
        if cap == Cap.CHANNEL_METADATA:
            data["channel"] = {"id": target.id, "title": "Kênh giả"}
        else:
            data["video_ids"] = list(self.ids)
        return FetchResult(normalized=Normalized.model_validate(data))


@pytest.fixture
def fake(monkeypatch: pytest.MonkeyPatch, data_dir: Path) -> dict:
    state: dict = {"feed": [], "listed": [], "started": []}
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: ChannelCollector(state["listed"])})
    monkeypatch.setattr(service, "fetch_feed", lambda _cid: list(state["feed"]))
    monkeypatch.setattr(service, "resolve", lambda t: (CHANNEL, "Việt Tân", "@VietTan"))
    monkeypatch.setattr(pipeline, "start", lambda job_id: state["started"].append(job_id))
    return state


def _entries(ids: list[str]) -> list[rss.FeedEntry]:
    return [rss.FeedEntry(v, f"Video {v}", datetime(2026, 11, 19, tzinfo=VN_TZ)) for v in ids]


def test_parse_feed() -> None:
    entries = rss.parse_feed(FEED)
    assert [e.video_id for e in entries] == ["vidAAAAAAA1", "vidAAAAAAA0"]
    assert entries[0].title == "Tin mới"
    assert entries[0].published_at.isoformat() == "2026-11-19T08:00:00+07:00"


def test_add_channel_queues_10_of_15_then_nothing(client: TestClient, fake, data_dir) -> None:
    ids = [_vid(i) for i in range(15)]
    fake["feed"], fake["listed"] = _entries(ids), ids
    r = client.post("/api/watchlist", json={"url": "https://www.youtube.com/@VietTan"})
    assert r.status_code == 201, r.text
    item = r.json()
    assert item["channel_id"] == CHANNEL and not item["initialized"]
    service.run_due()  # lần đầu: bước thêm kênh
    assert len(fake["started"]) == 10
    assert list((data_dir / "channels" / CHANNEL / "captures").iterdir())
    service.check(item["id"])  # lần sau: không có gì mới
    assert len(fake["started"]) == 10
    got = client.get("/api/watchlist").json()[0]
    assert got["initialized"] and got["latest_video"]["id"] in ids
    assert got["last_checked_at"].endswith("+07:00")


def test_one_new_entry_makes_one_job_once(client: TestClient, fake) -> None:
    fake["feed"] = _entries([_vid(0)])
    item = client.post("/api/watchlist", json={"url": "@VietTan"}).json()
    service.check(item["id"])
    before = len(fake["started"])
    fake["feed"] = _entries([_vid(1), _vid(0)])
    assert service.check(item["id"]) == [_vid(1)]
    assert service.check(item["id"]) == []
    assert len(fake["started"]) == before + 1
    events = client.get("/api/events").json()
    assert events[0]["kind"] == "new_video" and "Việt Tân" in events[0]["message"]
    assert events[0]["video_id"] == _vid(1)


def test_check_now_also_uses_channel_listing(client: TestClient, fake) -> None:
    item = client.post("/api/watchlist", json={"url": "@VietTan"}).json()
    service.check(item["id"])
    fake["listed"] = [_vid(7)]  # RSS còn cache, chưa có video này
    r = client.post(f"/api/watchlist/{item['id']}/check")
    assert r.status_code == 200 and r.json()["new_videos"] == [_vid(7)]


def test_crud_and_duplicate(client: TestClient, fake) -> None:
    item = client.post("/api/watchlist", json={"url": "@VietTan", "level": "text"}).json()
    assert item["level"] == "text"
    assert client.post("/api/watchlist", json={"url": "@VietTan"}).status_code == 409
    r = client.patch(f"/api/watchlist/{item['id']}", json={"enabled": False})
    assert r.json()["enabled"] is False
    service.run_due()  # mục đang tắt không được kiểm tra
    assert fake["started"] == []
    assert client.delete(f"/api/watchlist/{item['id']}").status_code == 204
    assert client.get("/api/watchlist").json() == []
    r = client.post("/api/watchlist", json={"url": "https://youtu.be/dQw4w9WgXcQ"})
    assert r.status_code == 400


def test_seed_defaults_once(data_dir) -> None:
    items = service.seed_defaults()
    assert [i.handle for i in items] == [
        "@VietTan",
        "@bbctiengviet",
        "@chantroimoimedia-u4s",
        "@luat-khoa",
    ]
    assert service.seed_defaults() == []
