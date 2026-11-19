"""API watchlist và dòng sự kiện (T30). Mọi thao tác ghi đều để lại dòng audit."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlmodel import Session, col, select

from h4wk.api.deps import current_actor
from h4wk.collectors.models import CollectLevel
from h4wk.core import audit
from h4wk.core.db import EventRow, JobRow, WatchItemRow, as_aware, get_engine
from h4wk.core.types import VnDatetime
from h4wk.watchlist import service, tasks

router = APIRouter(tags=["watchlist"])
ActorDep = Annotated[str, Depends(current_actor)]


class LatestVideo(BaseModel):
    id: str
    title: str
    published_at: VnDatetime | None


class WatchItem(BaseModel):
    id: str
    channel_id: str
    title: str
    handle: str | None
    enabled: bool
    level: CollectLevel
    initialized: bool
    last_checked_at: VnDatetime | None
    last_error: str | None
    latest_video: LatestVideo | None
    collected_count: int


class WatchCreate(BaseModel):
    url: str
    level: CollectLevel = CollectLevel.FULL


class WatchUpdate(BaseModel):
    enabled: bool | None = None
    level: CollectLevel | None = None


class CheckResult(BaseModel):
    new_videos: list[str]
    checked_at: VnDatetime


class EventJob(BaseModel):
    id: str
    status: str


class Event(BaseModel):
    id: int
    at: VnDatetime
    kind: str
    message: str
    watch_item: str | None
    video_id: str | None
    job: EventJob | None


def _aware(dt: datetime | None) -> datetime | None:
    return as_aware(dt) if dt else None


def _out(item: WatchItemRow) -> WatchItem:
    latest = service.latest_video(item.id)
    return WatchItem(
        id=item.id,
        channel_id=item.channel_id,
        title=item.title,
        handle=item.handle,
        enabled=item.enabled,
        level=CollectLevel(item.level),
        initialized=item.initialized,
        last_checked_at=_aware(item.last_checked_at),
        last_error=item.last_error,
        latest_video=LatestVideo(
            id=latest.video_id, title=latest.title, published_at=_aware(latest.published_at)
        )
        if latest
        else None,
        collected_count=service.collected_count(item.id),
    )


def _not_found(actor: str, action: str, item_id: str) -> HTTPException:
    audit.log(actor, action, item_id, {"error": "not found"}, status="error")
    return HTTPException(status.HTTP_404_NOT_FOUND, "watchlist item not found")


@router.get("/api/watchlist")
def list_watchlist() -> list[WatchItem]:
    return [_out(i) for i in service.list_items()]


@router.post("/api/watchlist", status_code=status.HTTP_201_CREATED)
def add_watch(body: WatchCreate, actor: ActorDep) -> WatchItem:
    """Thêm kênh; bước thêm kênh (thu hồ sơ, xử lý video mới nhất) chạy nền ngay sau đó."""
    try:
        item = service.add_channel(body.url, body.level)
    except service.Duplicate as e:
        audit.log(actor, "watchlist.add", body.url, {"error": str(e)}, status="error")
        raise HTTPException(status.HTTP_409_CONFLICT, str(e)) from None
    except Exception as e:
        audit.log(actor, "watchlist.add", body.url, {"error": str(e)}, status="error")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    audit.log(actor, "watchlist.add", item.id, {"channel_id": item.channel_id})
    tasks.check_item(item.id)
    return _out(item)


@router.patch("/api/watchlist/{item_id}")
def update_watch(item_id: str, body: WatchUpdate, actor: ActorDep) -> WatchItem:
    fields = body.model_dump(exclude_none=True)
    try:
        item = service.update_item(item_id, **fields)
    except service.NotFound:
        raise _not_found(actor, "watchlist.update", item_id) from None
    audit.log(actor, "watchlist.update", item_id, fields)
    return _out(item)


@router.delete("/api/watchlist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch(item_id: str, actor: ActorDep) -> Response:
    try:
        service.delete_item(item_id)
    except service.NotFound:
        raise _not_found(actor, "watchlist.delete", item_id) from None
    audit.log(actor, "watchlist.delete", item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/api/watchlist/{item_id}/check")
def check_now(item_id: str, actor: ActorDep) -> CheckResult:
    """Check now: RSS cộng danh sách video của kênh (không chờ cache RSS)."""
    try:
        new = service.check(item_id, listing=True)
    except service.NotFound:
        raise _not_found(actor, "watchlist.check", item_id) from None
    except Exception as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"check failed: {e}") from None
    audit.log(actor, "watchlist.check", item_id, {"new_videos": new})
    item = service.get_item(item_id)
    return CheckResult(new_videos=new, checked_at=_aware(item.last_checked_at))  # type: ignore[arg-type]


@router.get("/api/events")
def list_events(limit: int = 50) -> list[Event]:
    with Session(get_engine()) as s:
        rows = s.exec(
            select(EventRow).order_by(col(EventRow.id).desc()).limit(max(1, min(limit, 500)))
        ).all()
        jobs = {
            j.id: j
            for j in s.exec(
                select(JobRow).where(col(JobRow.id).in_([r.job_id for r in rows if r.job_id]))
            ).all()
        }
    return [
        Event(
            id=r.id or 0,
            at=as_aware(r.at),
            kind=r.kind,
            message=r.message,
            watch_item=r.watch_item,
            video_id=r.video_id,
            job=EventJob(id=r.job_id, status=jobs[r.job_id].status) if r.job_id in jobs else None,
        )
        for r in rows
    ]
