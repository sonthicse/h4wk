from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlmodel import Session

from h4wk.collectors.base import QuotaExceeded
from h4wk.core.db import QuotaRow, get_engine
from h4wk.core.types import VN_TZ

PROVIDER = "youtube_api"
DAILY_LIMIT = 10_000
STOP_RATIO = 0.9
PACIFIC = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class QuotaUsage:
    used: int
    limit: int
    resets_at: datetime


def period(now: datetime) -> str:
    return now.astimezone(PACIFIC).date().isoformat()


def resets_at(now: datetime) -> datetime:
    local = now.astimezone(PACIFIC)
    nxt = datetime.combine(local.date() + timedelta(days=1), time(0), tzinfo=PACIFIC)
    return nxt.astimezone(VN_TZ)


def _row(s: Session, now: datetime) -> QuotaRow:
    row = s.get(QuotaRow, PROVIDER)
    if row is None or row.period != period(now):
        return QuotaRow(provider=PROVIDER, period=period(now))
    return row


def usage(now: datetime) -> QuotaUsage:
    with Session(get_engine()) as s:
        used = _row(s, now).used
    return QuotaUsage(used=used, limit=DAILY_LIMIT, resets_at=resets_at(now))


def _ensure_period(s: Session, now: datetime) -> None:
    s.connection().execute(
        text(
            "INSERT INTO source_quota (provider, period, used) VALUES (:p, :period, 0) "
            "ON CONFLICT(provider) DO UPDATE SET period = excluded.period, used = 0 "
            "WHERE source_quota.period != excluded.period"
        ),
        {"p": PROVIDER, "period": period(now)},
    )


def spend(units: int, now: datetime) -> None:
    with Session(get_engine()) as s:
        _ensure_period(s, now)
        done = s.connection().execute(
            text("UPDATE source_quota SET used = used + :n WHERE provider = :p AND used < :stop"),
            {"n": units, "p": PROVIDER, "stop": int(DAILY_LIMIT * STOP_RATIO)},
        )
        used = s.get(QuotaRow, PROVIDER).used if done.rowcount == 0 else 0
        s.commit()
    if done.rowcount == 0:
        raise QuotaExceeded(f"YouTube API quota at {used}/{DAILY_LIMIT} units today")


def exhaust(now: datetime) -> None:
    with Session(get_engine()) as s:
        _ensure_period(s, now)
        s.connection().execute(
            text("UPDATE source_quota SET used = :limit WHERE provider = :p"),
            {"limit": DAILY_LIMIT, "p": PROVIDER},
        )
        s.commit()
