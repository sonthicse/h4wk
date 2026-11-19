"""Periodic task của watchlist: mỗi phút xem mục nào tới chu kỳ (check_interval_min)."""

from huey import crontab

from h4wk.jobs.queue import huey
from h4wk.watchlist import service


@huey.periodic_task(crontab(minute="*"))
def check_watchlist() -> None:
    service.run_due()


@huey.task()
def check_item(item_id: str) -> None:
    """Chạy ngay bước thêm kênh sau khi thêm, không chờ periodic task."""
    service.check(item_id)
