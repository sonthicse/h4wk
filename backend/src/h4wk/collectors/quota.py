"""Quota YouTube Data API đếm theo ngày, reset lúc nửa đêm giờ Pacific (SPEC 10.3).

Bộ đếm lưu trong database chỉ mục nên `reindex` sẽ đưa về 0 (Google vẫn tự chặn khi hết thật).
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlmodel import Session

from h4wk.collectors.base import QuotaExceeded
from h4wk.core.db import QuotaRow, get_engine
from h4wk.core.types import VN_TZ

PROVIDER = "youtube_api"
DAILY_LIMIT = 10_000
STOP_RATIO = 0.9  # dùng tới 90% thì ngừng
PACIFIC = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class QuotaUsage:
    used: int
    limit: int
    resets_at: datetime  # giờ Việt Nam


def period(now: datetime) -> str:
    return now.astimezone(PACIFIC).date().isoformat()


def resets_at(now: datetime) -> datetime:
    """Nửa đêm Pacific kế tiếp (zoneinfo tự xử lý giờ mùa hè)."""
    local = now.astimezone(PACIFIC)
    nxt = datetime.combine(local.date() + timedelta(days=1), time(0), tzinfo=PACIFIC)
    return nxt.astimezone(VN_TZ)


def _row(s: Session, now: datetime) -> QuotaRow:
    """Dòng của kỳ hiện tại; chưa có hoặc đã thuộc kỳ cũ thì coi như used = 0."""
    row = s.get(QuotaRow, PROVIDER)
    if row is None:
        return QuotaRow(provider=PROVIDER, period=period(now))
    if row.period != period(now):
        row.period, row.used = period(now), 0
    return row


def usage(now: datetime) -> QuotaUsage:
    with Session(get_engine()) as s:
        used = _row(s, now).used
    return QuotaUsage(used=used, limit=DAILY_LIMIT, resets_at=resets_at(now))


def spend(units: int, now: datetime) -> None:
    """Cộng quota đã dùng; từ 90% giới hạn trở lên thì ném QuotaExceeded và không cộng."""
    with Session(get_engine()) as s:
        row = _row(s, now)
        if row.used >= DAILY_LIMIT * STOP_RATIO:
            raise QuotaExceeded(f"YouTube API quota at {row.used}/{DAILY_LIMIT} units today")
        row.used += units
        s.add(row)
        s.commit()


def exhaust(now: datetime) -> None:
    """Google báo hết quota: coi như đã dùng hết cả ngày."""
    with Session(get_engine()) as s:
        row = _row(s, now)
        row.used = DAILY_LIMIT
        s.add(row)
        s.commit()
