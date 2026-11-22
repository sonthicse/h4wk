from datetime import datetime
from typing import Literal

from sqlmodel import Session

from h4wk.core.db import EventRow, get_engine
from h4wk.core.types import VN_TZ

EventKind = Literal["channel_added", "new_video", "job_done", "job_failed", "review"]


def record(kind: EventKind, message: str, **fields: str | None) -> None:
    with Session(get_engine()) as s:
        s.add(EventRow(at=datetime.now(VN_TZ), kind=kind, message=message, **fields))
        s.commit()
