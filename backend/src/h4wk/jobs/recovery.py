from datetime import datetime
from typing import Literal

from sqlalchemy import update
from sqlmodel import Session, select

from h4wk.core import audit
from h4wk.core.db import JobRow, get_engine
from h4wk.core.types import VN_TZ

Task = Literal["collect", "media", "analyze"]
QUEUE_TASKS: dict[str, set[str]] = {"default": {"collect", "analyze"}, "gpu": {"media"}}


def next_task(job: JobRow) -> Task:
    if job.step in (None, "collect"):
        return "media" if job.capture else "collect"
    if job.step == "analyze":
        return "analyze"
    return "analyze" if job.progress >= 70 else "media"


def recover(queue: Literal["default", "gpu"]) -> list[str]:
    from h4wk.jobs import pipeline

    with Session(get_engine()) as s:
        jobs = s.exec(select(JobRow).where(JobRow.status == "running")).all()
    started = {"collect": pipeline.collect, "media": pipeline.media, "analyze": pipeline.analyze}
    recovered = []
    for job in jobs:
        task = next_task(job)
        if task not in QUEUE_TASKS[queue]:
            continue
        with Session(get_engine()) as s:
            res = s.execute(
                update(JobRow)  # type: ignore[arg-type]
                .where(JobRow.id == job.id, JobRow.status == "running")  # type: ignore[arg-type]
                .values(status="queued", updated_at=datetime.now(VN_TZ))
            )
            s.commit()
        if res.rowcount != 1:
            continue
        audit.log("system:recovery", "job.recover", job.id, {"task": task, "step": job.step})
        started[task](job.id)
        recovered.append(job.id)
    return recovered
