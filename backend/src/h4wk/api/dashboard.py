"""Số liệu dashboard (T35), tính từ chỉ mục và thư mục data/videos/."""

from collections import Counter
from datetime import date, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, func, select

from h4wk.core.config import data_dir
from h4wk.core.db import WatchItemRow, get_engine
from h4wk.core.types import VN_TZ
from h4wk.evidence.writer import CAPTURE_TS_FORMAT, list_captures
from h4wk.jobs.pipeline import latest_findings
from h4wk.review.decisions import decisions_for
from h4wk.review.queue import video_ref

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


class TopVideo(BaseModel):
    id: str
    title: str | None
    channel: str | None
    score: int  # high 3, medium 2, low 1; bỏ nghi vấn đã bị bác
    findings: SeverityCounts


class Dashboard(BaseModel):
    channel_count: int
    video_count: int
    capture_count: int
    findings_by_severity: SeverityCounts
    findings_by_status: StatusCounts
    activity: list[DayActivity]  # 14 ngày, cũ trước, theo giờ Việt Nam
    youtube_quota: Usage | None  # có khi làm T14
    supadata_credits: Usage | None  # có khi làm T15
    top_video: TopVideo | None


def _day(capture: str) -> date:
    return datetime.strptime(capture, CAPTURE_TS_FORMAT).date()


@router.get("/api/dashboard")
def dashboard() -> Dashboard:
    with Session(get_engine()) as s:
        channel_count = s.exec(select(func.count()).select_from(WatchItemRow)).one()

    root = data_dir() / "videos"
    captures_by_video = {
        d.name: list_captures(d / "captures") for d in (root.iterdir() if root.is_dir() else [])
    }
    captures_by_video = {k: v for k, v in captures_by_video.items() if v}
    capture_days = Counter(_day(c) for caps in captures_by_video.values() for c in caps)

    findings = latest_findings()
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

    return Dashboard(
        channel_count=channel_count,
        video_count=len(captures_by_video),
        capture_count=sum(len(c) for c in captures_by_video.values()),
        findings_by_severity=SeverityCounts(**by_sev),
        findings_by_status=StatusCounts(**by_status),
        activity=[
            DayActivity(date=d, captures=capture_days[d], findings=finding_days[d]) for d in days
        ],
        youtube_quota=None,
        supadata_credits=None,
        top_video=top,
    )
