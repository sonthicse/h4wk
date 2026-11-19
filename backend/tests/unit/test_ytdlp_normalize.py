"""T9: chuyển dữ liệu thô của yt-dlp sang dữ liệu chung, không gọi mạng."""

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from yt_dlp.utils import DownloadError

from h4wk.collectors.base import Blocked, NotFound, Transient
from h4wk.collectors.models import TranscriptKind
from h4wk.collectors.providers import ytdlp as y

RAW = Path(__file__).resolve().parents[1] / "fixtures" / "raw" / "ytdlp"


@pytest.fixture
def info() -> dict:
    return json.loads((RAW / "video.info.json").read_text(encoding="utf-8"))


def test_video(info: dict) -> None:
    v = y.video_from_info(info)
    assert (v.id, v.channel_id, v.title) == (
        "h4wkDemo001",
        "UCh4wkDemoChannel000000",
        "Video thử nghiệm h4wk",
    )
    assert v.duration_s == 40 and v.view_count == 12 and v.comment_count == 3
    assert v.category == "News & Politics" and v.tags == ["thử nghiệm", "h4wk"]
    assert v.published_at == datetime.fromtimestamp(1795509000, UTC)
    assert v.published_at.utcoffset().total_seconds() == 7 * 3600  # giờ Việt Nam
    assert v.is_live is False and v.availability == "public"


def test_live_video(info: dict) -> None:
    assert y.video_from_info({**info, "live_status": "is_live"}).is_live


def test_comments_keep_replies(info: dict) -> None:
    cs = y.comments_from_info(info)
    assert [(c.id, c.parent_id) for c in cs] == [
        ("Ugw1", None),
        ("Ugw1.r1", "Ugw1"),
        ("Ugw2", None),
    ]
    assert cs[0].author_channel_id == "UCcommenter000000000001" and cs[0].like_count == 4
    assert cs[2].published_at is None


def test_subtitle_languages_only_vietnamese(info: dict) -> None:
    # bản người đăng tải lên (vi*) và bản tự động gốc vi-orig; không lấy bản dịch máy
    assert y.subtitle_langs(info) == (["vi"], ["vi-orig"])


def test_transcripts_from_json3(tmp_path: Path, info: dict) -> None:
    for f in RAW.glob("*.json3"):
        shutil.copy(f, tmp_path)
    ts = {t.kind: t for t in y.transcripts_from_dir(tmp_path, info["id"])}
    assert set(ts) == {TranscriptKind.UPLOADED, TranscriptKind.AUTO}
    auto = ts[TranscriptKind.AUTO]
    assert auto.lang == "vi"
    assert [(s.start, s.end, s.text) for s in auto.segments] == [
        (0.5, 2.1, "Hôm nay mình"),  # kết thúc khi câu sau bắt đầu
        (2.1, 7.1, "nói về Trần Văn Mẫu."),
    ]
    assert ts[TranscriptKind.UPLOADED].segments[0].text == "Phụ đề do người đăng tải lên"


def test_thumbnail_choice(info: dict) -> None:
    urls = y.thumbnail_urls(info)
    assert urls["maxres"] == "https://i.ytimg.com/vi/h4wkDemo001/maxresdefault.jpg"  # jpg lớn nhất
    assert urls["0"] == "https://i.ytimg.com/vi/h4wkDemo001/0.jpg"
    assert list(urls) == ["maxres", "0", "1", "2", "3"]


def test_channel_from_flat() -> None:
    flat = json.loads((RAW / "channel.flat.json").read_text(encoding="utf-8"))
    ch = y.channel_from_info(flat)
    assert (ch.id, ch.handle, ch.title) == (
        "UCh4wkDemoChannel000000",
        "@h4wkdemo",
        "Kênh thử nghiệm h4wk",
    )
    assert ch.subscriber_count == 1200 and ch.avatar_url == "https://yt3.ggpht.com/avatar"
    assert y.video_ids_from_flat(flat) == ["h4wkDemo001", "h4wkDemo002"]


@pytest.mark.parametrize(
    ("msg", "kind"),
    [
        ("ERROR: [youtube] x: Sign in to confirm you're not a bot", Blocked),
        ("ERROR: unable to download video data: HTTP Error 403: Forbidden", Blocked),
        ("ERROR: Unable to download video subtitles for 'ab': HTTP Error 429: Too Many", Blocked),
        ("ERROR: [youtube] x: Video unavailable", NotFound),
        ("ERROR: [youtube] x: Private video. Sign in if you've been granted access", NotFound),
        ("ERROR: [youtube] x: This video has been removed by the uploader", NotFound),
        ("ERROR: Read timed out. (read timeout=20.0)", Transient),
        ("ERROR: [Errno 101] Network is unreachable", Transient),
        ("ERROR: một lỗi lạ", Transient),
    ],
)
def test_classify_error(msg: str, kind: type) -> None:
    assert isinstance(y.classify_error(DownloadError(msg)), kind)


def test_channel_from_video_info() -> None:
    info = json.loads((RAW / "video.info.json").read_text(encoding="utf-8"))
    c = y.channel_from_video_info(info)
    assert c.title == "Kênh thử nghiệm h4wk" and c.handle == "@h4wkdemo"
    assert c.id == info["channel_id"] and c.description == ""
