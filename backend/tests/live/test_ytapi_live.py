"""T14: thu video và kênh thật bằng YouTube Data API (gọi mạng, tốn quota, chạy tay:
uv run pytest -m live -k ytapi). Cần YOUTUBE_API_KEY trong .env hoặc data/secrets.json."""

from pathlib import Path

import pytest

from h4wk.collectors.models import Cap, CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator, Settings
from h4wk.collectors.providers.youtube_api import MAX_LIST_VIDEOS, YouTubeApiCollector
from h4wk.collectors.targets import Target, TargetKind, parse_target
from h4wk.core import secrets
from h4wk.evidence.models import Manifest, SourceStatus, Trigger
from h4wk.evidence.verify import FileStatus, verify

# Video tiếng Việt công khai, đã dùng ở spike T2 và test live của yt-dlp.
VIDEO = "https://www.youtube.com/watch?v=oAFNS8b7br0"


@pytest.fixture(autouse=True)
def _need_key() -> None:
    if not secrets.get("YOUTUBE_API_KEY"):
        pytest.skip("Cần YOUTUBE_API_KEY để gọi YouTube Data API")


def _orchestrator(data_dir: Path) -> Orchestrator:
    return Orchestrator(
        {"youtube_api": YouTubeApiCollector()},
        Settings(priority={c: ["youtube_api"] for c in Cap}),
        root=data_dir,
    )


@pytest.mark.live
def test_ytapi_collects_text_level_video(data_dir: Path) -> None:
    cap = _orchestrator(data_dir).collect(
        parse_target(VIDEO),
        CollectLevel.TEXT,
        collector="user:test",
        trigger=Trigger(type="manual"),
    )
    m = Manifest.model_validate_json((cap / "manifest.json").read_text("utf-8"))
    n = Normalized.model_validate_json((cap / "normalized.json").read_text("utf-8"))
    status = {c.what: c.status for c in m.sources}
    assert status[Cap.VIDEO_METADATA] == SourceStatus.OK, m.sources
    assert status[Cap.COMMENTS] == SourceStatus.OK, m.sources
    assert status[Cap.THUMBNAILS] == SourceStatus.OK, m.sources
    assert status[Cap.TRANSCRIPTS] == SourceStatus.NO_SOURCE, m.sources
    assert n.video and n.video.id == "oAFNS8b7br0" and n.channel
    assert any(t.name == "maxres" for t in n.thumbnails)
    assert all(r.status == FileStatus.OK for r in verify(cap))


@pytest.mark.live
def test_ytapi_lists_channel_videos(data_dir: Path, tmp_path: Path) -> None:
    c = YouTubeApiCollector()
    video = c.fetch(Cap.VIDEO_METADATA, Target(TargetKind.VIDEO, "oAFNS8b7br0"), tmp_path)
    channel = Target(TargetKind.CHANNEL, video.normalized.video.channel_id)
    ids = c.fetch(Cap.CHANNEL_VIDEOS, channel, tmp_path).normalized.video_ids
    assert 0 < len(ids) <= MAX_LIST_VIDEOS
