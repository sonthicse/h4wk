"""Chạy lại job bị treo khi consumer khởi động (T46). Các bước của luồng là idempotent
nên job chạy tiếp từ bước dở dang, không thu lại hay xử lý lại bước đã xong.

Hạn chế: job đang chạy thật ở consumer khác cùng hàng đợi sẽ bị chạy trùng nếu chỉ khởi
động lại một consumer. Demo chạy một consumer mỗi hàng đợi nên chấp nhận."""

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
    """Bước cần chạy lại cho job đang running."""
    if job.step in (None, "collect"):
        return "media" if job.capture else "collect"
    if job.step == "analyze":
        return "analyze"
    return "analyze" if job.progress >= 70 else "media"


def recover(queue: Literal["default", "gpu"]) -> list[str]:
    """Đưa lại vào hàng đợi các job running có bước tiếp theo thuộc hàng đợi này."""
    from h4wk.jobs import pipeline

    with Session(get_engine()) as s:
        jobs = s.exec(select(JobRow).where(JobRow.status == "running")).all()
    started = {"collect": pipeline.collect, "media": pipeline.media, "analyze": pipeline.analyze}
    recovered = []
    for job in jobs:
        task = next_task(job)
        if task not in QUEUE_TASKS[queue]:
            continue
        # Giành job bằng update có điều kiện: mỗi worker đều gọi on_startup.
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
