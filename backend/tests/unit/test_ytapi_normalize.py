"""T14: chuyển response của YouTube Data API sang dữ liệu chung, không gọi mạng thật."""

import copy
import json
from pathlib import Path

import pytest

from h4wk.collectors import quota
from h4wk.collectors.base import Blocked, NotFound, QuotaExceeded, Transient, Unsupported
from h4wk.collectors.models import Cap
from h4wk.collectors.providers import youtube_api as y
from h4wk.collectors.targets import Target, TargetKind

RAW = Path(__file__).resolve().parents[1] / "fixtures" / "raw" / "ytapi"
VIDEO = Target(TargetKind.VIDEO, "h4wkDemo001")
CHANNEL = Target(TargetKind.CHANNEL, "UCh4wkDemoChannel000000")


def raw(name: str) -> dict:
    return json.loads((RAW / name).read_text(encoding="utf-8"))


@pytest.fixture
def video_item() -> dict:
    return raw("video.json")["items"][0]


@pytest.fixture
def channel_item() -> dict:
    return raw("channel.json")["items"][0]


def test_parse_duration() -> None:
    assert y.parse_duration("PT4M13S") == 253
    assert y.parse_duration("PT1H2M3S") == 3723
    assert y.parse_duration("P1DT1S") == 86401
    assert y.parse_duration("P0D") == 0
    assert y.parse_duration(None) is None


def test_video(video_item: dict) -> None:
    v = y.video_from_api(video_item)
    assert (v.id, v.channel_id, v.title) == (
        "h4wkDemo001",
        "UCh4wkDemoChannel000000",
        "Video thử nghiệm h4wk",
    )
    assert v.category == "News & Politics" and v.duration_s == 40
    assert v.tags == ["thử nghiệm", "h4wk"]
    assert v.published_at.utcoffset().total_seconds() == 7 * 3600
    assert (v.view_count, v.like_count, v.comment_count) == (12, 1, 3)
    assert v.availability == "public" and v.is_live is False


def test_video_live_and_missing_likes(video_item: dict) -> None:
    item = copy.deepcopy(video_item)
    item["snippet"]["liveBroadcastContent"] = "live"
    del item["statistics"]["likeCount"]
    v = y.video_from_api(item)
    assert v.is_live is True and v.like_count is None


def test_channel(channel_item: dict) -> None:
    c = y.channel_from_api(channel_item)
    assert c.id == "UCh4wkDemoChannel000000" and c.handle == "@h4wkdemo"
    assert c.avatar_url == "https://yt3.ggpht.com/h4wk/s800"
    assert c.banner_url == "https://yt3.googleusercontent.com/h4wk-banner"
    assert c.created_at.utcoffset().total_seconds() == 7 * 3600
    assert (c.subscriber_count, c.view_count, c.video_count) == (1200, 34567, 7)


def test_channel_hidden_subscribers(channel_item: dict) -> None:
    item = copy.deepcopy(channel_item)
    item["statistics"]["hiddenSubscriberCount"] = True
    assert y.channel_from_api(item).subscriber_count is None


def test_comments_merge_inline_and_full_replies() -> None:
    threads = raw("comment_threads.p1.json")["items"] + raw("comment_threads.p2.json")["items"]
    replies = {"Ugw2": raw("comment_replies.json")["items"]}
    cs = y.comments_from_api(threads, replies)
    assert [(c.id, c.parent_id) for c in cs] == [
        ("Ugw1", None),
        ("Ugw1.r1", "Ugw1"),
        ("Ugw2", None),
        ("Ugw2.r1", "Ugw2"),
        ("Ugw2.r2", "Ugw2"),
        ("Ugw2.r3", "Ugw2"),
    ]
    assert cs[0].author_channel_id == "UCcommenter000000000001" and cs[0].like_count == 4
    assert cs[0].text == "Video này có dấu hiệu lừa đảo."
    assert cs[0].published_at.utcoffset().total_seconds() == 7 * 3600


def test_comments_use_inline_replies_when_not_fetched_in_full() -> None:
    threads = raw("comment_threads.p2.json")["items"]
    assert [c.id for c in y.comments_from_api(threads, {})] == ["Ugw2", "Ugw2.r1"]


def test_thumbnails_largest_and_frames(video_item: dict) -> None:
    t = y.thumbnails_from_api(video_item)
    assert t["maxres"] == ("https://i.ytimg.com/vi/h4wkDemo001/maxresdefault.jpg", 1280, 720)
    assert t["0"] == ("https://i.ytimg.com/vi/h4wkDemo001/0.jpg", None, None)
    assert list(t) == ["maxres", "0", "1", "2", "3"]


def test_video_ids_capped() -> None:
    pages = [raw("playlist_items.p1.json"), raw("playlist_items.p2.json")]
    assert y.video_ids_from_pages(pages) == [f"h4wkDemo00{n}" for n in range(1, 6)]
    big = [
        {"items": [{"contentDetails": {"videoId": f"v{n}"}} for n in range(50)]} for _ in range(5)
    ]
    assert len(y.video_ids_from_pages(big)) == y.MAX_LIST_VIDEOS


@pytest.mark.parametrize(
    ("status", "body", "kind"),
    [
        (403, raw("error_quota.json"), QuotaExceeded),
        (404, raw("error_not_found.json"), NotFound),
        (400, raw("error_key_invalid.json"), Blocked),
        (403, raw("error_comments_disabled.json"), Blocked),
        (500, None, Transient),
        (503, None, Transient),
        (
            403,
            {"error": {"message": "slow down", "errors": [{"reason": "rateLimitExceeded"}]}},
            Transient,
        ),
    ],
)
def test_classify_error(status: int, body: dict | None, kind: type) -> None:
    err = y.classify_error(status, body)
    assert type(err) is kind
    assert f"YouTube API {status}" in str(err)


# ------------------------------------------------------------- collector qua MockTransport


def test_video_metadata(ytapi, tmp_path: Path) -> None:
    c = ytapi.collector()
    res = c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    assert res.normalized.video.id == "h4wkDemo001"
    assert res.normalized.channel.handle == "@h4wkdemo"
    assert res.cost.quota_units == 2
    assert (tmp_path / "h4wkDemo001.video.json").exists()
    assert (tmp_path / "UCh4wkDemoChannel000000.channel.json").exists()
    api = ytapi.api_requests()
    assert len(api) == 2
    for r in api:
        assert r.headers["x-goog-api-key"] == "test-key"
        assert "test-key" not in str(r.url)
    assert quota.usage(c.now()).used == 2


def test_thumbnails_reuse_cached_video_and_send_no_key(ytapi, tmp_path: Path) -> None:
    c = ytapi.collector()
    c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    before = len(ytapi.api_requests())
    res = c.fetch(Cap.THUMBNAILS, VIDEO, tmp_path)
    assert len(ytapi.api_requests()) == before  # không gọi lại videos.list
    assert res.cost.quota_units == 0
    images = [r for r in ytapi.requests if r.url.host == "i.ytimg.com"]
    assert len(images) == 5 and all("x-goog-api-key" not in r.headers for r in images)
    names = [t.name for t in res.normalized.thumbnails]
    assert names == ["maxres", "0", "1", "3"]  # ảnh "2" trả 404 nên bị bỏ qua
    assert (tmp_path / "maxres.jpg").exists() and (tmp_path / "3.jpg").exists()
    assert res.normalized.thumbnails[0].file == f"sources/{tmp_path.name}/maxres.jpg"


def test_comments_follow_pages_and_fetch_missing_replies(ytapi, tmp_path: Path) -> None:
    res = ytapi.collector().fetch(Cap.COMMENTS, VIDEO, tmp_path)
    assert [c.id for c in res.normalized.comments] == [
        "Ugw1",
        "Ugw1.r1",
        "Ugw2",
        "Ugw2.r1",
        "Ugw2.r2",
        "Ugw2.r3",
    ]
    paths = [r.url.path.rsplit("/", 1)[-1] for r in ytapi.api_requests()]
    assert paths == ["commentThreads", "commentThreads", "comments"]
    assert res.cost.quota_units == 3
    saved = json.loads((tmp_path / "h4wkDemo001.comments.json").read_text(encoding="utf-8"))
    assert len(saved["threads"]) == 2 and list(saved["replies"]) == ["Ugw2"]


def test_comments_disabled_is_empty_not_error(ytapi, tmp_path: Path) -> None:
    ytapi.override["commentThreads"] = (403, raw("error_comments_disabled.json"))
    res = ytapi.collector().fetch(Cap.COMMENTS, VIDEO, tmp_path)
    assert res.normalized.comments == []


def test_channel_videos_use_uploads_playlist(ytapi, tmp_path: Path) -> None:
    res = ytapi.collector().fetch(Cap.CHANNEL_VIDEOS, CHANNEL, tmp_path)
    assert res.normalized.video_ids == [f"h4wkDemo00{n}" for n in range(1, 6)]
    api = ytapi.api_requests()
    assert [r.url.path.rsplit("/", 1)[-1] for r in api] == [
        "channels",
        "playlistItems",
        "playlistItems",
    ]
    assert api[1].url.params["playlistId"] == "UUh4wkDemoChannel000000"
    assert not any("/search" in r.url.path for r in api)


def test_playlist_videos(ytapi, tmp_path: Path) -> None:
    pl = Target(TargetKind.PLAYLIST, "PLh4wkDemoPlaylist0001")
    res = ytapi.collector().fetch(Cap.PLAYLIST_VIDEOS, pl, tmp_path)
    assert len(res.normalized.video_ids) == 5
    assert ytapi.api_requests()[0].url.params["playlistId"] == pl.id


def test_channel_metadata(ytapi, tmp_path: Path) -> None:
    res = ytapi.collector().fetch(Cap.CHANNEL_METADATA, CHANNEL, tmp_path)
    assert res.normalized.channel.title == "Kênh thử nghiệm h4wk"


def test_missing_key_is_blocked(ytapi, tmp_path: Path) -> None:
    with pytest.raises(Blocked, match="YOUTUBE_API_KEY is not set"):
        ytapi.collector(key=lambda: None).fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    assert ytapi.requests == []


def test_unknown_video_is_not_found(ytapi, tmp_path: Path) -> None:
    ytapi.override["videos"] = (200, {"items": []})
    with pytest.raises(NotFound, match="h4wkDemo001"):
        ytapi.collector().fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)


def test_cap_must_match_target_kind(ytapi, tmp_path: Path) -> None:
    with pytest.raises(Unsupported):
        ytapi.collector().fetch(Cap.COMMENTS, CHANNEL, tmp_path)
    with pytest.raises(Unsupported):
        ytapi.collector().fetch(Cap.TRANSCRIPTS, VIDEO, tmp_path)
    with pytest.raises(Unsupported):
        ytapi.collector().fetch(Cap.CHANNEL_VIDEOS, VIDEO, tmp_path)


def test_quota_exceeded_stops_following_calls(ytapi, tmp_path: Path) -> None:
    ytapi.override["videos"] = (403, raw("error_quota.json"))
    c = ytapi.collector()
    with pytest.raises(QuotaExceeded):
        c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    seen = len(ytapi.requests)
    with pytest.raises(QuotaExceeded):
        c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
    assert len(ytapi.requests) == seen  # lần sau bị chặn tại chỗ, không gọi mạng


def test_transport_error_is_transient(tmp_path: Path, data_dir: Path) -> None:
    import httpx2

    from h4wk.collectors.providers.youtube_api import YouTubeApiCollector

    def boom(request):  # noqa: ANN001, ANN202
        raise httpx2.ConnectError("down", request=request)

    c = YouTubeApiCollector(
        client=httpx2.Client(transport=httpx2.MockTransport(boom)), key=lambda: "k"
    )
    with pytest.raises(Transient):
        c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)


def test_health_check(ytapi, data_dir: Path) -> None:
    assert ytapi.collector().health_check().detail == "quota 1/10000 units today"
    assert ytapi.collector(key=lambda: None).health_check().ok is False
    ytapi.override["videos"] = (400, raw("error_key_invalid.json"))
    h = ytapi.collector().health_check()
    assert h.ok is False and "keyInvalid" in h.detail and "test-key" not in h.detail


def test_maxres_falls_back_when_largest_listed_thumbnail_is_missing(
    ytapi, video_item: dict, tmp_path: Path
) -> None:
    # Thực tế: API liệt kê "fhd" 1920x1080 nhưng ảnh đó trả 404.
    item = copy.deepcopy(video_item)
    item["snippet"]["thumbnails"]["fhd"] = {
        "url": "https://i.ytimg.com/vi/h4wkDemo001/fhddefault.jpg",
        "width": 1920,
        "height": 1080,
    }
    ytapi.override["videos"] = (200, {"items": [item]})
    res = ytapi.collector().fetch(Cap.THUMBNAILS, VIDEO, tmp_path)
    maxres = res.normalized.thumbnails[0]
    assert maxres.name == "maxres" and maxres.url.endswith("/maxresdefault.jpg")
    assert maxres.width == 1280


def test_non_json_200_is_transient(ytapi, tmp_path: Path) -> None:
    import httpx2

    c = ytapi.collector()
    c.client = httpx2.Client(
        transport=httpx2.MockTransport(lambda r: httpx2.Response(200, text="<html>oops</html>"))
    )
    with pytest.raises(Transient, match="non-JSON"):
        c.fetch(Cap.VIDEO_METADATA, VIDEO, tmp_path)
