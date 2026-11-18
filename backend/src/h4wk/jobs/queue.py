"""Hàng đợi Huey lưu bằng SQLite trong thư mục dữ liệu. Hai hàng đợi: default và gpu.

uv run huey_consumer h4wk.jobs.queue.huey -w 2
uv run huey_consumer h4wk.jobs.queue.huey_gpu -w 1
"""

from huey import SqliteHuey

from h4wk.core.config import data_dir

_root = data_dir()
_root.mkdir(parents=True, exist_ok=True)
huey = SqliteHuey("h4wk", filename=str(_root / "queue.db"))
huey_gpu = SqliteHuey("h4wk-gpu", filename=str(_root / "queue_gpu.db"))

# Đăng ký các task với consumer.
from h4wk.jobs import pipeline  # noqa: E402, F401
