"""Hàng đợi Huey lưu bằng SQLite trong thư mục dữ liệu. Hai hàng đợi: default và gpu.

uv run huey_consumer h4wk.jobs.queue.huey -w 2
uv run huey_consumer h4wk.jobs.queue.huey_gpu -w 1

Khi consumer khởi động, job đang running được đưa lại vào hàng đợi (xem recovery.py).
"""

import logging
import threading

from huey import SqliteHuey

from h4wk.core.config import data_dir

_root = data_dir()
_root.mkdir(parents=True, exist_ok=True)
huey = SqliteHuey("h4wk", filename=str(_root / "queue.db"))
huey_gpu = SqliteHuey("h4wk-gpu", filename=str(_root / "queue_gpu.db"))

# Đăng ký các task với consumer.
from h4wk.jobs import pipeline  # noqa: E402, F401
from h4wk.watchlist import tasks  # noqa: E402, F401

_log = logging.getLogger(__name__)


_recover_lock = threading.Lock()
_recovered: set[str] = set()


def _recover(queue: str) -> None:
    """Mỗi hàng đợi chỉ recover một lần mỗi tiến trình: Huey gọi on_startup ở từng worker."""
    from h4wk.jobs import recovery

    with _recover_lock:
        if queue in _recovered:
            return
        _recovered.add(queue)
    try:
        recovery.recover(queue)  # type: ignore[arg-type]
    except Exception:
        _log.exception("Không chạy lại được job bị treo (hàng đợi %s)", queue)


@huey.on_startup()
def _recover_default() -> None:
    _recover("default")


@huey_gpu.on_startup()
def _recover_gpu() -> None:
    _recover("gpu")
