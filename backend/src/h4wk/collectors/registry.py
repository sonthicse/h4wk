"""Danh sách nguồn thu. Thêm một adapter: một file trong providers/ và một dòng ở đây."""

from collections.abc import Callable

from h4wk.collectors.base import Collector

# tên nguồn → hàm tạo adapter
COLLECTORS: dict[str, Callable[[], Collector]] = {}
