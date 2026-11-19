"""API rà soát (T25): hàng đợi và quyết định. Mỗi quyết định ghi audit, kể cả khi lỗi."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from h4wk.analysis.models import ReviewDecision, SourceKind
from h4wk.api.deps import current_actor
from h4wk.core import audit, events
from h4wk.review import decisions
from h4wk.review.queue import QueueItem, ReviewStatus, queue

router = APIRouter(tags=["review"])
ActorDep = Annotated[str, Depends(current_actor)]


class DecisionBody(BaseModel):
    status: Literal["confirmed", "rejected", "needs_info"]
    note: str = ""


@router.get("/api/review/queue")
def review_queue(
    video: str | None = None,
    source_kind: SourceKind | None = None,
    status: ReviewStatus | None = None,
    latest_only: bool = False,
) -> list[QueueItem]:
    """latest_only=true: chỉ bản thu mới nhất của mỗi video (thu lại không làm lặp nghi vấn)."""
    return queue(video, source_kind, status, latest_only)


@router.get("/api/findings/{finding_id}/decisions")
def finding_decisions(finding_id: str) -> list[ReviewDecision]:
    return decisions.decisions_for([finding_id]).get(finding_id, [])


@router.post("/api/findings/{finding_id}/decision")
def decide(finding_id: str, body: DecisionBody, actor: ActorDep) -> ReviewDecision:
    def fail(code: int, msg: str) -> HTTPException:
        audit.log(actor, "review.decide", finding_id, {"error": msg}, status="error")
        return HTTPException(code, msg)

    try:
        d = decisions.record(finding_id, body.status, body.note, actor)
    except decisions.NotFound:
        raise fail(status.HTTP_404_NOT_FOUND, "finding not found") from None
    except ValidationError:
        raise fail(status.HTTP_422_UNPROCESSABLE_CONTENT, "Reject needs a note") from None
    audit.log(actor, "review.decide", finding_id, {"status": d.status, "note": d.note})
    f = decisions.finding(finding_id)
    events.record(
        "review",
        f"{actor.removeprefix('user:')} marked a {f.category} finding as {d.status}",
        video_id=f.video_id,
    )
    return d
