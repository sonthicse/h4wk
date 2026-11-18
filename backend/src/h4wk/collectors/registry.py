"""Danh sách nguồn thu. Thêm một adapter: một file trong providers/ và một dòng ở đây."""

from collections.abc import Callable

from h4wk.collectors.base import Collector
from h4wk.collectors.providers import ytdlp

# tên nguồn → hàm tạo adapter
COLLECTORS: dict[str, Callable[[], Collector]] = {
    "ytdlp": ytdlp.from_config,
}
