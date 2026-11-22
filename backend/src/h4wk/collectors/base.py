"""Quy ước adapter nguồn thu: giao diện Collector và năm loại lỗi."""

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from h4wk.collectors.models import Cap, Normalized
from h4wk.evidence.models import Cost

if TYPE_CHECKING:
    from h4wk.collectors.targets import Target


class CollectorError(Exception):
    """Lỗi của nguồn thu. Orchestrator dựa vào loại lỗi để thử lại hay chuyển nguồn."""


class Transient(CollectorError):
    """Lỗi tạm thời (mạng, timeout): thử lại tối đa 3 lần rồi chuyển nguồn."""


class Blocked(CollectorError):
    """Bị chặn (bot check, 403): chuyển nguồn ngay."""


class QuotaExceeded(CollectorError):
    """Hết quota hoặc credit: chuyển nguồn ngay."""


class NotFound(CollectorError):
    """Video hoặc kênh không tồn tại, hoặc không công khai: không thử nguồn khác."""


class Unsupported(CollectorError):
    """Nguồn không lấy được loại dữ liệu này cho mục tiêu này: thử nguồn tiếp theo."""


@dataclass(frozen=True)
class FetchResult:
    """Phần dữ liệu chung lấy được cho một Cap. Dữ liệu thô đã được ghi vào workdir."""

    normalized: Normalized
    cost: Cost | None = None


@dataclass(frozen=True)
class Health:
    ok: bool
    detail: str = ""


class Collector(Protocol):
    name: str
    capabilities: set[Cap]
    version: str | None

    def fetch(self, cap: Cap, target: "Target", workdir: Path) -> FetchResult: ...

    def health_check(self) -> Health: ...
