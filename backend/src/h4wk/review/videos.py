from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlmodel import Session, select

from h4wk.analysis.models import Finding, VideoReviewDecision, VideoVerdict
from h4wk.core.config import data_dir
from h4wk.core.db import VideoDecisionRow, get_engine
from h4wk.core.types import VN_TZ, CaptureTs
from h4wk.jobs.pipeline import _latest_runs
from h4wk.review.decisions import NotFound
from h4wk.review.queue import ReviewStatus, VideoRef, _video

_FINDINGS = TypeAdapter(list[Finding])


class Changed(Exception):
    pass


class VideoVerdictDetail(BaseModel):
    verdict: VideoVerdict
    status: ReviewStatus
    decisions: list[VideoReviewDecision]
    findings: list[Finding]


class VideoQueueItem(BaseModel):
    video: VideoRef
    capture: CaptureTs
    run_id: str
    verdict: VideoVerdict
    status: ReviewStatus
    finding_count: int
    decisions: list[VideoReviewDecision]


def _load(root: Path, video_id: str, capture: str, run_id: str):
    folder = root / "videos" / video_id / "derived" / capture / "analysis" / run_id
    try:
        verdict = VideoVerdict.model_validate_json(
            (folder / "verdict.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        raise NotFound(video_id) from error
    if (verdict.video_id, verdict.capture, verdict.run_id) != (video_id, capture, run_id):
        raise NotFound(video_id)
    return verdict, folder / "findings.json"


def _decisions(session: Session, video_id: str | None = None):
    query = select(VideoDecisionRow).order_by(VideoDecisionRow.id.desc())
    if video_id is not None:
        query = query.where(VideoDecisionRow.video_id == video_id)
    result = {}
    for row in session.exec(query):
        result.setdefault((row.video_id, row.run_id), []).append(
            VideoReviewDecision.model_validate_json(row.data)
        )
    return result


def _latest(video_id: str):
    root = data_dir()
    latest = _latest_runs(root)
    capture = max((cap for vid, cap in latest if vid == video_id), default=None)
    if capture is None:
        raise NotFound(video_id)
    return _load(root, video_id, capture, latest[video_id, capture])


def _findings(path: Path, verdict: VideoVerdict) -> list[Finding]:
    try:
        rows = _FINDINGS.validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError):
        return []
    return [
        f
        for f in rows
        if (f.video_id, f.capture, f.run_id) == (verdict.video_id, verdict.capture, verdict.run_id)
    ]


def detail(video_id: str) -> VideoVerdictDetail:
    verdict, path = _latest(video_id)
    with Session(get_engine()) as session:
        decisions = _decisions(session, video_id).get((video_id, verdict.run_id), [])
    return VideoVerdictDetail(
        verdict=verdict,
        status=decisions[0].status if decisions else "unreviewed",
        decisions=decisions,
        findings=sorted(_findings(path, verdict), key=lambda f: (f.start is None, f.start or 0)),
    )


def queue(status: ReviewStatus | None = None, latest_only: bool = True) -> list[VideoQueueItem]:
    root = data_dir()
    runs = _latest_runs(root)
    newest = {}
    for video_id, capture in runs:
        newest[video_id] = max(newest.get(video_id, ""), capture)
    with Session(get_engine()) as session:
        decisions = _decisions(session)
    items = []
    for (video_id, capture), run_id in runs.items():
        if latest_only and capture != newest[video_id]:
            continue
        try:
            verdict, path = _load(root, video_id, capture, run_id)
        except NotFound:
            continue
        if verdict.violation == "no":
            continue
        history = decisions.get((video_id, run_id), [])
        current = history[0].status if history else "unreviewed"
        if status is None or current == status:
            items.append(
                VideoQueueItem(
                    video=_video(video_id, capture),
                    capture=capture,
                    run_id=run_id,
                    verdict=verdict,
                    status=current,
                    decisions=history,
                    finding_count=len(_findings(path, verdict)),
                )
            )
    severity = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        items,
        key=lambda item: (
            item.status != "unreviewed",
            severity[item.verdict.severity],
            -item.verdict.at.timestamp(),
            item.video.id,
        ),
    )


def record(video_id: str, run_id: str, status: str, note: str, actor: str):
    verdict, _ = _latest(video_id)
    if verdict.run_id != run_id:
        raise Changed(run_id)
    decision = VideoReviewDecision(
        video_id=video_id,
        run_id=run_id,
        status=status,
        by=actor,
        note=note,
        at=datetime.now(VN_TZ),
    )
    line = decision.model_dump_json()
    with Session(get_engine()) as session:
        with (data_dir() / "reviews.jsonl").open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        session.add(VideoDecisionRow(video_id=video_id, run_id=run_id, data=line))
        session.commit()
    return decision, _video(video_id, verdict.capture)
