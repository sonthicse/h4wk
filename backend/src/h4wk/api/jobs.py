"""API thu thập, job và nghi vấn (T12)."""

import re
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from h4wk.analysis.models import Finding
from h4wk.api.deps import current_actor
from h4wk.collectors.models import CollectLevel
from h4wk.collectors.targets import TargetKind, parse_target
from h4wk.core import audit
from h4wk.core.db import JobRow, as_aware, get_session
from h4wk.evidence.models import Manifest
from h4wk.jobs import pipeline

router = APIRouter(tags=["jobs"])
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[str, Depends(current_actor)]


class CollectBody(BaseModel):
    url: str
    level: CollectLevel = CollectLevel.FULL
    force: bool = False


class Job(BaseModel):
    id: str
    target: str
    video_id: str
    level: str
    trigger: str
    status: str
    step: str | None
    progress: int
    capture: str | None
    run_id: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def of(cls, row: JobRow) -> "Job":
        data = row.model_dump()
        data["created_at"] = as_aware(row.created_at)
        data["updated_at"] = as_aware(row.updated_at)
        return cls.model_validate(data)


@router.post("/api/collect", status_code=status.HTTP_202_ACCEPTED)
def collect(body: CollectBody, actor: ActorDep) -> list[Job]:
    """Link video: một job. Link playlist: mỗi video một job (tối đa playlist_max_videos)."""

    def reject(code: int, msg: str) -> HTTPException:
        audit.log(actor, "job.create", body.url, {"error": msg}, status="error")
        return HTTPException(code, msg)

    try:
        target = parse_target(body.url)
    except ValueError as e:
        raise reject(400, str(e)) from None
    if target.kind == TargetKind.VIDEO:
        videos = [(target.url, target.id)]
        extra: dict[str, str] = {}
    elif target.kind == TargetKind.PLAYLIST:
        try:
            ids = pipeline.playlist_video_ids(target.id)
        except Exception as e:
            raise reject(502, f"could not list playlist videos: {e}") from None
        if not ids:
            raise reject(400, "playlist has no videos")
        videos = [(parse_target(i).url, i) for i in ids]
        extra = {"playlist": target.id}
    else:
        raise reject(
            400,
            f"collecting a {target.kind} is not supported here; add the channel to the watchlist",
        )
    jobs = []
    for url, video_id in videos:
        job = pipeline.create_job(url, video_id, body.level, body.force, actor)
        audit.log(actor, "job.create", job.id, {"url": url, "level": body.level, **extra})
        pipeline.start(job.id)
        with Session(pipeline.get_engine()) as s:
            row = s.get(JobRow, job.id)
            assert row is not None
            jobs.append(Job.of(row))
    return jobs


class ReanalyzeBody(BaseModel):
    # Bỏ trống: mọi video đã có bản thu xử lý xong.
    video_ids: list[str] | None = None


@router.post("/api/reanalyze", status_code=status.HTTP_202_ACCEPTED)
def reanalyze(body: ReanalyzeBody, actor: ActorDep, session: SessionDep) -> list[Job]:
    """Phân tích lại bản thu mới nhất đã có timeline, không thu lại hay chạy media. Dùng sau
    khi sửa đối tượng hoặc từ điển."""
    root = pipeline.data_dir() / "videos"
    ids = body.video_ids
    if ids is None:
        ids = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    jobs = []
    for video_id in ids:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", video_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid video id: {video_id}")
        cap = pipeline.prepared_capture(video_id)
        if cap is None:
            if body.video_ids is not None:
                error = {"error": "no prepared capture"}
                audit.log(actor, "job.reanalyze", video_id, error, status="error")
                raise HTTPException(
                    status.HTTP_409_CONFLICT, f"video {video_id} has no processed capture yet"
                )
            continue
        manifest = (root / video_id / "captures" / cap / "manifest.json").read_bytes()
        level = Manifest.model_validate_json(manifest).level
        job = pipeline.create_reanalyze_job(video_id, cap, level, actor)
        audit.log(actor, "job.reanalyze", job.id, {"video_id": video_id, "capture": cap})
        row = session.get(JobRow, job.id)
        assert row is not None
        session.refresh(row)
        jobs.append(Job.of(row))
    return jobs


@router.get("/api/jobs")
def list_jobs(session: SessionDep) -> list[Job]:
    q = select(JobRow).order_by(JobRow.created_at.desc())  # type: ignore[union-attr]
    return [Job.of(r) for r in session.exec(q).all()]


@router.get("/api/jobs/{job_id}")
def get_job(job_id: str, session: SessionDep) -> Job:
    row = session.get(JobRow, job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return Job.of(row)


@router.get("/api/findings")
def findings(latest_only: bool = False) -> list[Finding]:
    """latest_only=true: chỉ bản thu mới nhất của mỗi video."""
    return pipeline.latest_findings(latest_only)
