from datetime import datetime

from sqlalchemy import update
from sqlmodel import Session, col, func, select

from h4wk.core.config import config_dir
from h4wk.core.config_models import SourcesConfig, load_toml
from h4wk.core.db import JobRow, get_engine
from h4wk.core.types import VN_TZ

WATCH_PREFIX = "system:watchlist:"
ACTIVE = ("queued", "running")


def threads_per_channel() -> int:
    path = config_dir() / "sources.toml"
    cfg = load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()
    return cfg.watchlist.threads_per_channel


def fill(trigger: str) -> list[str]:
    from h4wk.jobs import pipeline

    started = []
    limit = threads_per_channel()
    while True:
        with Session(get_engine()) as s:
            active = s.exec(
                select(func.count()).where(
                    JobRow.trigger == trigger, col(JobRow.status).in_(ACTIVE)
                )
            ).one()
            if active >= limit:
                return started
            nxt = s.exec(
                select(JobRow.id)
                .where(JobRow.trigger == trigger, JobRow.status == "waiting")
                .order_by(col(JobRow.created_at))
            ).first()
            if nxt is None:
                return started
            res = s.execute(
                update(JobRow)  # type: ignore[arg-type]
                .where(JobRow.id == nxt, JobRow.status == "waiting")  # type: ignore[arg-type]
                .values(status="queued", updated_at=datetime.now(VN_TZ))
            )
            s.commit()
        if res.rowcount == 1:
            pipeline.start(nxt)
            started.append(nxt)


def fill_all() -> None:
    with Session(get_engine()) as s:
        triggers = s.exec(select(JobRow.trigger).where(JobRow.status == "waiting").distinct()).all()
    for trigger in triggers:
        fill(trigger)


def worker_threads() -> int:
    from h4wk.watchlist.service import load_channels

    channels = sum(1 for c in load_channels() if c.enabled)
    return max(4, channels * threads_per_channel() + 2)
