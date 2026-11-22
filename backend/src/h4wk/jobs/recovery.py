"""Chạy lại job bị treo khi consumer khởi động (T46). Các bước của luồng là idempotent
nên job chạy tiếp từ bước dở dang, không thu lại hay xử lý lại bước đã xong.

Chỉ job "running" (đang chạy thật khi tiến trình chết) được đưa lại; job "queued" vẫn nằm
trong Huey nên không đụng tới. Mỗi hàng đợi recover một lần mỗi tiến trình (nhiều worker
trong cùng consumer không recover lặp), xem queue.py.

Hạn chế:
- Job đang chạy thật ở consumer khác cùng hàng đợi sẽ bị chạy trùng nếu chỉ khởi động lại
  một consumer. Demo chạy một consumer mỗi hàng đợi nên chấp nhận.
- Job force=True treo sau khi orch.collect ghi bản thu nhưng trước khi lưu capture vào job
  thì recover tạo thêm bản thu thứ hai.
- Analyze treo sau khi đã ghi FindingRow thì chạy lại sinh run mới (API chỉ lấy run mới nhất).
- Tiến trình chết đúng giữa lúc đặt queued và lúc đưa vào hàng đợi thì job kẹt ở queued."""

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
