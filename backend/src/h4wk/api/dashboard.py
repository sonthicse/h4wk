"""Số liệu dashboard (T35), tính từ chỉ mục và thư mục data/videos/."""

from collections import Counter
from datetime import date, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel, Field

from h4wk.analysis import jev_log
from h4wk.collectors import quota
from h4wk.collectors.providers import supadata
from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ
from h4wk.evidence.writer import CAPTURE_TS_FORMAT, list_captures
from h4wk.jobs.pipeline import latest_findings
from h4wk.review.decisions import decisions_for
from h4wk.review.queue import video_ref
from h4wk.review.videos import queue as video_queue
from h4wk.watchlist import service as watchlist

router = APIRouter(tags=["dashboard"])

ACTIVITY_DAYS = 14
_SCORE = {"high": 3, "medium": 2, "low": 1}


class SeverityCounts(BaseModel):
    high: int = 0
    medium: int = 0
    low: int = 0


class StatusCounts(BaseModel):
    unreviewed: int = 0
    confirmed: int = 0
    rejected: int = 0
    needs_info: int = 0


class DayActivity(BaseModel):
    date: date
    captures: int
    findings: int


class Usage(BaseModel):
    used: int
    limit: int


class JevMonthUsage(BaseModel):
    """Tổng tháng hiện tại theo giờ Việt Nam, chỉ gồm token TypeSafe báo."""

    requests: int
    input_tokens: int | None = Field(description="Input tokens reported by TypeSafe, if available.")
    output_tokens: int | None = Field(
        description="Output tokens reported by TypeSafe, if available."
    )


class TopVideo(BaseModel):
    id: str
    title: str | None
    channel: str | None
    score: int
    findings: SeverityCounts


class Dashboard(BaseModel):
    channel_count: int
    video_count: int
    capture_count: int
    findings_by_severity: SeverityCounts
    findings_by_status: StatusCounts
    videos_by_review_status: StatusCounts
    activity: list[DayActivity]
    youtube_quota: Usage | None
    supadata_credits: Usage | None
    jev_usage: JevMonthUsage | None
    top_video: TopVideo | None


def _day(capture: str) -> date:
    return datetime.strptime(capture, CAPTURE_TS_FORMAT).date()


@router.get("/api/dashboard")
def dashboard(latest_only: bool = False) -> Dashboard:
    """latest_only=true: số nghi vấn và video nổi bật chỉ tính bản thu mới nhất mỗi video."""
    channel_count = len(watchlist.load_channels())

    root = data_dir() / "videos"
    captures_by_video = {
        d.name: list_captures(d / "captures") for d in (root.iterdir() if root.is_dir() else [])
    }
    captures_by_video = {k: v for k, v in captures_by_video.items() if v}
    capture_days = Counter(_day(c) for caps in captures_by_video.values() for c in caps)

    findings = latest_findings(latest_only)
    decisions = decisions_for([f.id for f in findings])
    status = {
        f.id: decisions[f.id][0].status if f.id in decisions else "unreviewed" for f in findings
    }
    by_sev = Counter(f.severity for f in findings)
    by_status = Counter(status.values())
    finding_days = Counter(_day(f.capture) for f in findings)

    today = datetime.now(VN_TZ).date()
    days = [today - timedelta(days=i) for i in range(ACTIVITY_DAYS - 1, -1, -1)]

    per_video: dict[str, Counter[str]] = {}
    for f in findings:
        if status[f.id] != "rejected":
            per_video.setdefault(f.video_id, Counter())[f.severity] += 1
    top = None
    if per_video:
        views = {}
        refs = {}
        for vid in per_video:
            refs[vid] = video_ref(vid)
            views[vid] = refs[vid].view_count or 0
        best = max(
            per_video,
            key=lambda v: (sum(_SCORE[k] * n for k, n in per_video[v].items()), views[v]),
        )
        top = TopVideo(
            id=best,
            title=refs[best].title,
            channel=refs[best].channel,
            score=sum(_SCORE[k] * n for k, n in per_video[best].items()),
            findings=SeverityCounts(**per_video[best]),
        )

    now = datetime.now(VN_TZ)
    u = quota.usage(now)
    jev = jev_log.summarize(jev_log.read(jev_log.month_start(now), now))["total"]
    c = supadata.credits_usage()
    return Dashboard(
        channel_count=channel_count,
        video_count=len(captures_by_video),
        capture_count=sum(len(c) for c in captures_by_video.values()),
        findings_by_severity=SeverityCounts(**by_sev),
        findings_by_status=StatusCounts(**by_status),
        videos_by_review_status=StatusCounts(**Counter(i.status for i in video_queue())),
        activity=[
            DayActivity(date=d, captures=capture_days[d], findings=finding_days[d]) for d in days
        ],
        youtube_quota=Usage(used=u.used, limit=u.limit),
        supadata_credits=Usage(used=c.used, limit=c.limit) if c else None,
        jev_usage=JevMonthUsage(
            requests=jev["requests"],
            input_tokens=jev.get("input_tokens"),
            output_tokens=jev.get("output_tokens"),
        )
        if jev["requests"]
        else None,
        top_video=top,
    )
