"""T14: bộ đếm quota YouTube API theo ngày giờ Pacific."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from h4wk.collectors import quota
from h4wk.collectors.base import QuotaExceeded
from h4wk.core.types import VN_TZ

NOON = datetime(2026, 11, 19, 10, 0, tzinfo=VN_TZ)


def test_period_changes_at_pacific_midnight() -> None:
    # 2026-11-19 15:00 +07:00 = 00:00 PST (UTC-8) ngày 19
    before = datetime(2026, 11, 19, 14, 59, tzinfo=VN_TZ)
    after = datetime(2026, 11, 19, 15, 0, tzinfo=VN_TZ)
    assert quota.period(before) == "2026-11-18"
    assert quota.period(after) == "2026-11-19"
    assert quota.resets_at(NOON) == after


def test_resets_at_follows_daylight_saving() -> None:
    # giờ mùa hè (PDT, UTC-7): nửa đêm Pacific là 14:00 giờ Việt Nam
    assert quota.resets_at(datetime(2026, 7, 1, 10, 0, tzinfo=VN_TZ)) == datetime(
        2026, 7, 1, 14, 0, tzinfo=VN_TZ
    )


def test_spend_accumulates_and_new_period_resets(data_dir: Path) -> None:
    quota.spend(3, NOON)
    quota.spend(2, NOON)
    assert quota.usage(NOON).used == 5
    assert quota.usage(NOON).limit == 10_000
    later = NOON + timedelta(days=1)
    assert quota.usage(later).used == 0
    quota.spend(1, later)
    assert quota.usage(later).used == 1


def test_stops_at_ninety_percent(data_dir: Path) -> None:
    quota.spend(8999, NOON)
    quota.spend(1, NOON)  # 8999 < 9000: còn được dùng
    assert quota.usage(NOON).used == 9000
    with pytest.raises(QuotaExceeded, match="9000/10000"):
        quota.spend(1, NOON)
    assert quota.usage(NOON).used == 9000


def test_exhaust_blocks_further_spending(data_dir: Path) -> None:
    quota.exhaust(NOON)
    assert quota.usage(NOON).used == 10_000
    with pytest.raises(QuotaExceeded):
        quota.spend(1, NOON)


def test_concurrent_spend_loses_no_update(data_dir: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def work() -> None:
        for _ in range(25):
            quota.spend(1, NOON)

    quota.usage(NOON)
    with ThreadPoolExecutor(4) as ex:
        for f in [ex.submit(work) for _ in range(4)]:
            f.result()
    assert quota.usage(NOON).used == 100
