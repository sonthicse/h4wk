"""Hàng đợi rà soát: nghi vấn của lần chạy mới nhất cho mỗi bản thu, kèm trạng thái."""

from typing import Literal

from pydantic import BaseModel, ValidationError

from h4wk.analysis.models import Finding, ReviewDecision
from h4wk.collectors.models import Normalized
from h4wk.core.config import data_dir
from h4wk.jobs.pipeline import latest_findings
from h4wk.review.decisions import decisions_for

ReviewStatus = Literal["unreviewed", "confirmed", "rejected", "needs_info"]
_SEVERITY = {"high": 0, "medium": 1, "low": 2}


class VideoRef(BaseModel):
    id: str
    title: str | None = None
    channel: str | None = None
    view_count: int | None = None


class QueueItem(BaseModel):
    finding: Finding
    status: ReviewStatus
    video: VideoRef
    decisions: list[ReviewDecision]


def _video(video_id: str, capture: str) -> VideoRef:
    path = data_dir() / "videos" / video_id / "captures" / capture / "normalized.json"
    try:
        n = Normalized.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return VideoRef(id=video_id)
    return VideoRef(
        id=video_id,
        title=n.video.title if n.video else None,
        channel=n.channel.title if n.channel else None,
        view_count=n.video.view_count if n.video else None,
    )


def video_ref(video_id: str) -> VideoRef:
    """Tiêu đề và kênh theo bản thu mới nhất có metadata video."""
    from h4wk.evidence.writer import list_captures

    for cap in reversed(list_captures(data_dir() / "videos" / video_id / "captures")):
        ref = _video(video_id, cap)
        if ref.title is not None:
            return ref
    return VideoRef(id=video_id)


def queue(
    video: str | None = None,
    source_kind: str | None = None,
    status: str | None = None,
    latest_only: bool = False,
) -> list[QueueItem]:
    findings = [
        f
        for f in latest_findings(latest_only)
        if (video is None or f.video_id == video)
        and (source_kind is None or f.source_kind == source_kind)
    ]
    decisions = decisions_for([f.id for f in findings])
    videos: dict[tuple[str, str], VideoRef] = {}
    items = []
    for f in findings:
        ds = decisions.get(f.id, [])
        item_status = ds[0].status if ds else "unreviewed"
        if status is not None and item_status != status:
            continue
        key = (f.video_id, f.capture)
        if key not in videos:
            videos[key] = _video(*key)
        items.append(QueueItem(finding=f, status=item_status, video=videos[key], decisions=ds))
    items.sort(
        key=lambda i: (
            _SEVERITY[i.finding.severity],
            i.finding.video_id,
            i.finding.start if i.finding.start is not None else -1.0,
        )
    )
    return items
