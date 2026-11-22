from huey import crontab

from h4wk.jobs.queue import huey
from h4wk.watchlist import service


@huey.periodic_task(crontab(minute="*"))
def check_watchlist() -> None:
    service.run_due()


@huey.task()
def check_item(item_id: str) -> None:
    service.check(item_id)
