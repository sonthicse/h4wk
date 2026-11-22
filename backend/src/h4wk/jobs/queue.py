import logging
import threading

from huey import SqliteHuey

from h4wk.core.config import data_dir

_root = data_dir()
_root.mkdir(parents=True, exist_ok=True)
huey = SqliteHuey("h4wk", filename=str(_root / "queue.db"))
huey_gpu = SqliteHuey("h4wk-gpu", filename=str(_root / "queue_gpu.db"))

from h4wk.jobs import pipeline  # noqa: E402, F401
from h4wk.watchlist import tasks  # noqa: E402, F401

_log = logging.getLogger(__name__)


_recover_lock = threading.Lock()
_recovered: set[str] = set()


def _recover(queue: str) -> None:
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
    from h4wk.jobs import lanes

    try:
        lanes.fill_all()
    except Exception:
        _log.exception("Không đưa được job chờ của watchlist vào hàng đợi")


@huey_gpu.on_startup()
def _recover_gpu() -> None:
    _recover("gpu")
