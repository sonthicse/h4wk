"""Điều phối thu thập: mỗi loại dữ liệu lấy từ một nguồn, thử các nguồn đang bật
theo thứ tự ưu tiên, chuyển nguồn khi lỗi, rồi ghi bản thu qua CaptureWriter."""

import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from sqlmodel import Session

from h4wk.collectors import registry
from h4wk.collectors.base import (
    Blocked,
    Collector,
    CollectorError,
    NotFound,
    QuotaExceeded,
    Transient,
    Unsupported,
)
from h4wk.collectors.models import Cap, CollectLevel, Normalized
from h4wk.collectors.targets import Target, TargetKind
from h4wk.core.config import config_dir
from h4wk.core.config_models import SourcesConfig, load_toml
from h4wk.core.db import SourceStateRow, as_aware, get_engine
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import SourceCall, SourceStatus, Trigger
from h4wk.evidence.writer import CaptureWriter

TRANSIENT_RETRIES = 3
SUSPEND_AFTER = 5
SUSPEND_FOR = timedelta(minutes=30)

LEVEL_CAPS: dict[CollectLevel, list[Cap]] = {
    CollectLevel.METADATA: [Cap.VIDEO_METADATA, Cap.THUMBNAILS],
    CollectLevel.TEXT: [Cap.VIDEO_METADATA, Cap.THUMBNAILS, Cap.TRANSCRIPTS, Cap.COMMENTS],
    CollectLevel.FULL: [
        Cap.VIDEO_METADATA,
        Cap.THUMBNAILS,
        Cap.TRANSCRIPTS,
        Cap.COMMENTS,
        Cap.MEDIA,
    ],
}
CHANNEL_CAPS = [Cap.CHANNEL_METADATA, Cap.CHANNEL_VIDEOS]

CAP_FIELDS: dict[Cap, list[str]] = {
    Cap.VIDEO_METADATA: ["video", "channel"],
    Cap.CHANNEL_METADATA: ["channel"],
    Cap.CHANNEL_VIDEOS: ["video_ids"],
    Cap.PLAYLIST_VIDEOS: ["video_ids"],
    Cap.TRANSCRIPTS: ["transcripts"],
    Cap.COMMENTS: ["comments"],
    Cap.THUMBNAILS: ["thumbnails"],
    Cap.MEDIA: ["media"],
}
_ERROR_STATUS: list[tuple[type[CollectorError], SourceStatus]] = [
    (Transient, SourceStatus.FAILED),
    (Blocked, SourceStatus.BLOCKED),
    (QuotaExceeded, SourceStatus.QUOTA_EXCEEDED),
    (NotFound, SourceStatus.NOT_FOUND),
    (Unsupported, SourceStatus.UNSUPPORTED),
]
_COUNTED = (Transient, Blocked, QuotaExceeded)


@dataclass
class Settings:
    priority: dict[Cap, list[str]]
    enabled: dict[str, bool] = field(default_factory=dict)
    fault_injection: set[str] = field(default_factory=set)

    @classmethod
    def from_sources(cls, cfg: SourcesConfig, registered: list[str]) -> "Settings":
        sections = cfg.sources.model_dump()
        priority = {}
        for cap in Cap:
            listed = [str(s) for s in cfg.priority.get(cap, [])]
            priority[cap] = listed + [n for n in registered if n not in listed]
        return cls(
            priority=priority,
            enabled={n: s["enabled"] for n, s in sections.items()},
            fault_injection={n for n, s in sections.items() if s["fault_injection"]},
        )


class SourceState:
    """Đếm lỗi liên tiếp và tạm ngưng nguồn, lưu trong database chỉ mục."""

    def __init__(self, now: Callable[[], datetime]) -> None:
        self.now = now

    def _get(self, s: Session, provider: str) -> SourceStateRow:
        return s.get(SourceStateRow, provider) or SourceStateRow(provider=provider)

    def suspended(self, provider: str) -> bool:
        with Session(get_engine()) as s:
            until = self._get(s, provider).suspended_until
        return until is not None and as_aware(until) > self.now()

    def record(self, provider: str, failed: bool, error: str | None = None) -> None:
        with Session(get_engine()) as s:
            row = self._get(s, provider)
            if error is not None:
                row.last_error, row.last_error_at = error, self.now()
            if failed:
                row.consecutive_failures += 1
                if row.consecutive_failures >= SUSPEND_AFTER:
                    row.suspended_until = self.now() + SUSPEND_FOR
                    row.consecutive_failures = 0
            else:
                row.consecutive_failures = 0
            s.add(row)
            s.commit()


class _Workdirs(Protocol):
    def workdir(self, name: str) -> Path: ...


class _TempWorkdirs:
    """Thư mục tạm cho dữ liệu thô khi không lưu bản thu."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def workdir(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path


class Orchestrator:
    def __init__(
        self,
        collectors: dict[str, Collector],
        settings: Settings,
        root: Path,
        now: Callable[[], datetime] = lambda: datetime.now(VN_TZ),
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.collectors = collectors
        self.settings = settings
        self.root = root
        self.now = now
        self.sleep = sleep
        self.state = SourceState(now)

    @classmethod
    def from_config(
        cls, root: Path, sources: SourcesConfig | None = None, **kwargs: object
    ) -> "Orchestrator":
        if sources is None:
            path = config_dir() / "sources.toml"
            sources = load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()
        collectors = {name: make() for name, make in registry.COLLECTORS.items()}
        settings = Settings.from_sources(sources, list(collectors))
        return cls(collectors, settings, root, **kwargs)  # type: ignore[arg-type]

    def collect(
        self, target: Target, level: CollectLevel, *, collector: str, trigger: Trigger
    ) -> Path:
        """Thu một video hoặc hồ sơ kênh (theo channel_id) và trả về thư mục bản thu đã khoá.
        Với kênh, mức thu không áp dụng: luôn lấy metadata kênh và danh sách video."""
        if target.kind == TargetKind.VIDEO:
            base, caps = self.root / "videos" / target.id, LEVEL_CAPS[level]
        elif target.kind == TargetKind.CHANNEL:
            base, caps = self.root / "channels" / target.id, CHANNEL_CAPS
        else:
            raise ValueError(
                f"orchestrator cannot collect a {target.kind}; use a video or channel id"
            )
        writer = CaptureWriter(
            base / "captures",
            source_url=target.url,
            collector=collector,
            trigger=trigger,
            level=level,
            now=self.now(),
        )
        try:
            merged: dict = {"schema": "h4wk.normalized/1", "provenance": {}}
            calls: list[SourceCall] = []
            for cap in caps:
                provider, part = self._collect_cap(cap, target, writer, calls)
                if provider and part is not None:
                    for f in CAP_FIELDS[cap]:
                        merged[f] = getattr(part, f)
                    merged["provenance"][cap] = provider
            normalized = Normalized.model_validate(merged)
        except BaseException:
            writer.abort()
            raise
        return writer.finalize(normalized, calls)

    def list_video_ids(self, target: Target) -> list[str]:
        """ID video của một playlist, không lưu bản thu (người dùng đã quyết). Thử nguồn theo
        thứ tự ưu tiên của Cap.PLAYLIST_VIDEOS; dữ liệu thô ghi vào thư mục tạm rồi bỏ."""
        if target.kind != TargetKind.PLAYLIST:
            raise ValueError(f"list_video_ids needs a playlist, got a {target.kind}")
        with tempfile.TemporaryDirectory() as tmp:
            _provider, part = self._collect_cap(
                Cap.PLAYLIST_VIDEOS, target, _TempWorkdirs(Path(tmp)), []
            )
        if part is None:
            raise RuntimeError("no source returned the playlist videos")
        return list(dict.fromkeys(part.video_ids))

    def _collect_cap(
        self, cap: Cap, target: Target, writer: _Workdirs, calls: list[SourceCall]
    ) -> tuple[str | None, Normalized | None]:
        candidates = [
            n
            for n in self.settings.priority.get(cap, [])
            if n in self.collectors and cap in self.collectors[n].capabilities
        ]
        for name in candidates:
            if not self.settings.enabled.get(name, True):
                calls.append(SourceCall(provider=name, what=cap, status=SourceStatus.DISABLED))
                continue
            if self.state.suspended(name):
                calls.append(SourceCall(provider=name, what=cap, status=SourceStatus.SUSPENDED))
                continue
            result, stop = self._try_source(name, cap, target, writer, calls)
            if result is not None:
                return name, result
            if stop:
                return None, None
        calls.append(SourceCall(provider=None, what=cap, status=SourceStatus.NO_SOURCE))
        return None, None

    def _try_source(
        self, name: str, cap: Cap, target: Target, writer: _Workdirs, calls: list[SourceCall]
    ) -> tuple[Normalized | None, bool]:
        """Trả về (dữ liệu, dừng hẳn loại dữ liệu này hay không)."""
        source = self.collectors[name]
        for attempt in range(TRANSIENT_RETRIES + 1):
            started = self.now()
            t0 = time.monotonic()
            try:
                if name in self.settings.fault_injection:
                    raise Blocked("fault_injection")
                result = source.fetch(cap, target, writer.workdir(name))
            except CollectorError as e:
                status = next(st for tp, st in _ERROR_STATUS if isinstance(e, tp))
                calls.append(self._call(name, cap, status, started, t0, error=str(e)))
                self.state.record(name, failed=isinstance(e, _COUNTED), error=str(e))
                if isinstance(e, Transient) and attempt < TRANSIENT_RETRIES:
                    self.sleep(2**attempt)
                    continue
                return None, isinstance(e, NotFound)
            calls.append(self._call(name, cap, SourceStatus.OK, started, t0, cost=result.cost))
            self.state.record(name, failed=False)
            return result.normalized, False
        return None, False

    def _call(
        self,
        name: str,
        cap: Cap,
        status: SourceStatus,
        started: datetime,
        t0: float,
        **extra: object,
    ) -> SourceCall:
        return SourceCall(
            provider=name,
            what=cap,
            status=status,
            started_at=started,
            duration_ms=int((time.monotonic() - t0) * 1000),
            version=self.collectors[name].version,
            **extra,
        )
