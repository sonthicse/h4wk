from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from h4wk.collectors.models import Cap, Normalized
from h4wk.evidence.models import Cost

if TYPE_CHECKING:
    from h4wk.collectors.targets import Target


class CollectorError(Exception):
    pass


class Transient(CollectorError):
    pass


class Blocked(CollectorError):
    pass


class QuotaExceeded(CollectorError):
    pass


class NotFound(CollectorError):
    pass


class Unsupported(CollectorError):
    pass


@dataclass(frozen=True)
class FetchResult:
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
