"""Dòng sự kiện (T30, T35): kèm tiêu đề video, tên kênh, số nghi vấn, lỗi để giao diện
không phải tra thêm."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlmodel import Session, col, func, select

from h4wk.core.db import EventRow, FindingRow, JobRow, WatchItemRow, as_aware, get_engine
from h4wk.core.events import EventKind
from h4wk.core.types import VnDatetime
from h4wk.review.queue import VideoRef, video_ref

router = APIRouter(tags=["events"])

JobStatus = Literal["queued", "running", "done", "failed"]


class EventJob(BaseModel):
    id: str
    status: JobStatus


class Event(BaseModel):
    id: int
    at: VnDatetime
    kind: EventKind
    message: str
    watch_item: str | None
    video_id: str | None
    video_title: str | None
    channel_title: str | None
    findings: int | None  # job_done: số nghi vấn của lần chạy
    error: str | None  # job_failed
    job: EventJob | None


@router.get("/api/events")
def list_events(limit: int = 50) -> list[Event]:
    with Session(get_engine()) as s:
        rows = s.exec(
            select(EventRow).order_by(col(EventRow.id).desc()).limit(max(1, min(limit, 500)))
        ).all()
        job_ids = [r.job_id for r in rows if r.job_id]
        jobs = {j.id: j for j in s.exec(select(JobRow).where(col(JobRow.id).in_(job_ids))).all()}
        run_ids = [j.run_id for j in jobs.values() if j.run_id]
        counts = dict(
            s.exec(
                select(FindingRow.run_id, func.count())
                .where(col(FindingRow.run_id).in_(run_ids))
                .group_by(FindingRow.run_id)
            ).all()
        )
        items = {w.id: w for w in s.exec(select(WatchItemRow)).all()}
    videos: dict[str, VideoRef] = {}
    out = []
    for r in rows:
        video = None
        if r.video_id:
            if r.video_id not in videos:
                videos[r.video_id] = video_ref(r.video_id)
            video = videos[r.video_id]
        job = jobs.get(r.job_id) if r.job_id else None
        item = items.get(r.watch_item) if r.watch_item else None
        out.append(
            Event(
                id=r.id or 0,
                at=as_aware(r.at),
                kind=r.kind,  # type: ignore[arg-type]
                message=r.message,
                watch_item=r.watch_item,
                video_id=r.video_id,
                video_title=video.title if video else None,
                channel_title=(item.title if item else None) or (video.channel if video else None),
                findings=counts.get(job.run_id, 0) if job and r.kind == "job_done" else None,
                error=job.error if job and r.kind == "job_failed" else None,
                job=EventJob(id=job.id, status=job.status) if job else None,  # type: ignore[arg-type]
            )
        )
    return out
