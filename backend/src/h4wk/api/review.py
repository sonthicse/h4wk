"""API rà soát (T25): hàng đợi và quyết định. Mỗi quyết định ghi audit, kể cả khi lỗi."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ValidationError

from h4wk.analysis.models import ReviewDecision, SourceKind, VideoReviewDecision
from h4wk.api.deps import current_actor
from h4wk.core import audit, events
from h4wk.review import decisions, videos
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


class VideoDecisionBody(DecisionBody):
    run_id: str


@router.get("/api/review/videos")
def video_queue(
    status: ReviewStatus | None = None, latest_only: bool = True
) -> list[videos.VideoQueueItem]:
    return videos.queue(status, latest_only)


@router.get("/api/videos/{video_id}/verdict", responses={404: {"description": "Verdict not found"}})
def video_verdict(video_id: str) -> videos.VideoVerdictDetail:
    try:
        return videos.detail(video_id)
    except decisions.NotFound:
        raise HTTPException(404, "verdict not found") from None


@router.post(
    "/api/videos/{video_id}/decision",
    responses={404: {"description": "Verdict not found"}, 409: {"description": "Verdict changed"}},
)
def decide_video(video_id: str, body: VideoDecisionBody, actor: ActorDep) -> VideoReviewDecision:
    def fail(code: int, message: str) -> HTTPException:
        audit.log(actor, "review.decide_video", video_id, {"error": message}, status="error")
        return HTTPException(code, message)

    try:
        decision, video = videos.record(video_id, body.run_id, body.status, body.note, actor)
    except decisions.NotFound:
        raise fail(404, "verdict not found") from None
    except videos.Changed:
        raise fail(409, "verdict changed, reload") from None
    except ValidationError:
        raise fail(422, "Reject needs a note") from None
    audit.log(actor, "review.decide_video", video_id, decision.model_dump(mode="json"))
    user = actor.removeprefix("user:")
    events.record(
        "review",
        f"{user} marked the verdict of {video.title or video_id} as {decision.status}",
        video_id=video_id,
    )
    return decision
