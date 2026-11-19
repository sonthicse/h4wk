"""API đọc video đã thu: danh sách, chi tiết, timeline, transcript, comment, media, khung hình.
Chỉ đọc file trong data/videos/; không sửa gì."""

import json
import re
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ValidationError

from h4wk.collectors.models import Cap, Channel, Comment, Normalized, Transcript, Video
from h4wk.core.config import data_dir
from h4wk.core.types import VnDatetime
from h4wk.evidence.models import Manifest
from h4wk.evidence.writer import list_captures
from h4wk.jobs.pipeline import latest_findings
from h4wk.media.timeline import Timeline

router = APIRouter(prefix="/api/videos", tags=["videos"])

_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_FRAME = re.compile(r"^[0-9]{6,}\.jpg$")


class SeverityCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class VideoSummary(BaseModel):
    id: str
    title: str
    channel: str | None
    published_at: VnDatetime | None
    view_count: int | None
    findings: SeverityCounts
    latest_capture: str


class CaptureSummary(BaseModel):
    id: str
    level: str
    collected_at: VnDatetime
    transcript_kinds: list[str]
    comment_count: int
    keyframe_count: int
    has_media: bool
    has_timeline: bool


class VideoDetail(BaseModel):
    video: Video
    channel: Channel | None
    captures: list[CaptureSummary]  # cũ trước, mới sau


def _not_found(what: str = "video") -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


def _video_dir(video_id: str) -> Path:
    if not _VIDEO_ID.match(video_id):
        raise _not_found()
    d = data_dir() / "videos" / video_id
    if not list_captures(d / "captures"):
        raise _not_found()
    return d


def _captures(d: Path) -> list[str]:
    return list_captures(d / "captures")


def _capture(d: Path, capture: str | None) -> str:
    caps = _captures(d)
    if capture is None:
        return caps[-1]
    if capture not in caps:
        raise _not_found("capture")
    return capture


def _normalized(d: Path, capture: str) -> Normalized | None:
    try:
        path = d / "captures" / capture / "normalized.json"
        return Normalized.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return None


def _latest_with_video(d: Path) -> tuple[str, Normalized] | None:
    """Bản thu mới nhất có metadata video."""
    for cap in reversed(_captures(d)):
        n = _normalized(d, cap)
        if n is not None and n.video is not None:
            return cap, n
    return None


def _derived_transcripts(d: Path, capture: str) -> list[Transcript]:
    folder = d / "derived" / capture / "transcripts"
    out = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            out.append(Transcript.model_validate_json(path.read_text(encoding="utf-8")))
        except ValidationError:
            continue
    return out


@router.get("")
def list_videos() -> list[VideoSummary]:
    counts: dict[str, Counter[str]] = {}
    for f in latest_findings():
        counts.setdefault(f.video_id, Counter())[f.severity] += 1
    root = data_dir() / "videos"
    out = []
    for d in sorted(root.iterdir()) if root.is_dir() else []:
        found = _latest_with_video(d)
        if found is None:
            continue
        cap, n = found
        assert n.video is not None
        out.append(
            VideoSummary(
                id=n.video.id,
                title=n.video.title,
                channel=n.channel.title if n.channel else None,
                published_at=n.video.published_at,
                view_count=n.video.view_count,
                findings=SeverityCounts(**counts.get(d.name, {})),
                latest_capture=_captures(d)[-1],
            )
        )
    out.sort(key=lambda v: v.latest_capture, reverse=True)
    return out


@router.get("/{video_id}")
def get_video(video_id: str) -> VideoDetail:
    d = _video_dir(video_id)
    found = _latest_with_video(d)
    if found is None:
        raise _not_found()
    _, latest = found
    captures = []
    for cap in _captures(d):
        try:
            manifest = Manifest.model_validate_json(
                (d / "captures" / cap / "manifest.json").read_text(encoding="utf-8")
            )
        except (OSError, ValidationError):
            continue
        n = _normalized(d, cap)
        kinds = [t.kind for t in (n.transcripts if n else [])]
        kinds += [t.kind for t in _derived_transcripts(d, cap) if t.kind not in kinds]
        index = d / "derived" / cap / "frames" / "index.json"
        frames = (
            json.loads(index.read_text(encoding="utf-8")).get("frames", [])
            if index.is_file()
            else []
        )
        captures.append(
            CaptureSummary(
                id=cap,
                level=manifest.level,
                collected_at=manifest.collected_at,
                transcript_kinds=kinds,
                comment_count=len(n.comments) if n else 0,
                keyframe_count=len(frames),
                has_media=_media_path(d, cap) is not None,
                has_timeline=(d / "derived" / cap / "timeline.json").is_file(),
            )
        )
    assert latest.video is not None
    return VideoDetail(video=latest.video, channel=latest.channel, captures=captures)


def _candidates(d: Path, capture: str | None) -> list[str]:
    """Bản thu được chỉ định, hoặc mọi bản thu từ mới tới cũ để rơi về bản có dữ liệu."""
    return [_capture(d, capture)] if capture else list(reversed(_captures(d)))


def _media_path(d: Path, cap: str) -> Path | None:
    proxy = d / "derived" / cap / "proxy_480p.mp4"
    if proxy.is_file():
        return proxy
    n = _normalized(d, cap)
    for m in n.media if n else []:
        if m.kind == "video" and (d / "captures" / cap / m.file).is_file():
            return d / "captures" / cap / m.file
    return None


@router.get("/{video_id}/timeline")
def get_timeline(video_id: str, capture: str | None = None) -> Timeline:
    """Timeline (C3) của bản thu chỉ định, mặc định là bản thu mới nhất đã có timeline."""
    d = _video_dir(video_id)
    for cap in _candidates(d, capture):
        path = d / "derived" / cap / "timeline.json"
        if path.is_file():
            return Timeline.model_validate_json(path.read_text(encoding="utf-8"))
    raise _not_found("timeline")


@router.get("/{video_id}/transcripts")
def get_transcripts(video_id: str, capture: str | None = None) -> list[Transcript]:
    """Transcript của bản thu chỉ định, mặc định là bản thu mới nhất có transcript."""
    d = _video_dir(video_id)
    for cap in _candidates(d, capture):
        n = _normalized(d, cap)
        found = [*(n.transcripts if n else []), *_derived_transcripts(d, cap)]
        if found:
            return found
    return []


@router.get("/{video_id}/comments")
def get_comments(video_id: str, capture: str | None = None) -> list[Comment]:
    """Comment phẳng theo C2, reply có parent_id. Mặc định lấy bản thu mới nhất đã thu comment."""
    d = _video_dir(video_id)
    for cap in _candidates(d, capture):
        n = _normalized(d, cap)
        if n is not None and Cap.COMMENTS in n.provenance:
            return n.comments
    return []


@router.get("/{video_id}/media", response_class=FileResponse)
def get_media(video_id: str, capture: str | None = None) -> FileResponse:
    """Bản proxy 480p nếu đã có, nếu không thì file video gốc. Hỗ trợ Range."""
    d = _video_dir(video_id)
    for cap in _candidates(d, capture):
        path = _media_path(d, cap)
        if path is not None:
            return FileResponse(path, media_type="video/mp4")
    raise _not_found("media")


@router.get("/{video_id}/frames/{file}", response_class=FileResponse)
def get_frame(video_id: str, file: str, capture: str | None = None) -> FileResponse:
    d = _video_dir(video_id)
    if _FRAME.match(file):
        for cap in _candidates(d, capture):
            path = d / "derived" / cap / "frames" / file
            if path.is_file():
                return FileResponse(path, media_type="image/jpeg")
    raise _not_found("frame")
