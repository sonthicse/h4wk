"""Ghi bản thu theo C1 (SPEC 10.2).

Adapter ghi dữ liệu thô vào thư mục tạm cùng ổ đĩa. `finalize` ghi normalized.json, tính
SHA-256, ghi manifest sau cùng, `rename` sang captures/<ts> trong một bước, rồi khoá chỉ đọc.
"""

import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from h4wk.collectors.models import Normalized
from h4wk.core.types import VN_TZ, CollectLevel
from h4wk.evidence.models import FileEntry, Manifest, SourceCall, Trigger

TMP_PREFIX = ".tmp-"
CAPTURE_TS_FORMAT = "%Y%m%dT%H%M%S"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def list_captures(captures_dir: Path) -> list[str]:
    """Các bản thu đã hoàn tất, theo thứ tự thời gian (bỏ qua thư mục tạm)."""
    if not captures_dir.is_dir():
        return []
    return sorted(
        p.name for p in captures_dir.iterdir() if p.is_dir() and not p.name.startswith(TMP_PREFIX)
    )


def lock_readonly(path: Path) -> None:
    """Chống sửa nhầm: file 0444, thư mục 0555. Không chống được người cố tình sửa."""
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            os.chmod(Path(root) / f, 0o444)
        for d in dirs:
            os.chmod(Path(root) / d, 0o555)
    os.chmod(path, 0o555)


class CaptureWriter:
    """Một lần thu: mở thư mục tạm, adapter ghi vào `workdir(provider)`, rồi `finalize`."""

    def __init__(
        self,
        captures_dir: Path,
        *,
        source_url: str,
        collector: str,
        trigger: Trigger,
        level: CollectLevel | str,
        now: datetime | None = None,
    ) -> None:
        self.captures_dir = captures_dir
        self.source_url = source_url
        self.collector = collector
        self.trigger = trigger
        self.level = level
        self.collected_at = (now or datetime.now(VN_TZ)).astimezone(VN_TZ)
        captures_dir.mkdir(parents=True, exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix=TMP_PREFIX, dir=captures_dir))

    def workdir(self, provider: str) -> Path:
        d = self.tmp / "sources" / provider
        d.mkdir(parents=True, exist_ok=True)
        return d

    def abort(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def finalize(self, normalized: Normalized, source_calls: list[SourceCall]) -> Path:
        target = self.captures_dir / self.collected_at.strftime(CAPTURE_TS_FORMAT)
        try:
            if target.exists():
                raise FileExistsError(f"bản thu đã tồn tại: {target}")
            previous = list_captures(self.captures_dir)
            (self.tmp / "normalized.json").write_text(
                normalized.model_dump_json(indent=2), encoding="utf-8"
            )
            files = {
                p.relative_to(self.tmp).as_posix(): FileEntry(
                    sha256=sha256_file(p), bytes=p.stat().st_size
                )
                for p in sorted(self.tmp.rglob("*"))
                if p.is_file()
            }
            manifest = Manifest.model_validate(
                {
                    "schema": "h4wk.manifest/1",
                    "source_url": self.source_url,
                    "collected_at": self.collected_at,
                    "collector": self.collector,
                    "trigger": self.trigger,
                    "level": self.level,
                    "tool_version": f"h4wk {version('h4wk')}",
                    "sources": source_calls,
                    "files": files,
                    "previous_capture": previous[-1] if previous else None,
                }
            )
            (self.tmp / "manifest.json").write_text(
                manifest.model_dump_json(indent=2), encoding="utf-8"
            )
            os.rename(self.tmp, target)  # cùng ổ đĩa nên là một bước
        except BaseException:
            self.abort()
            raise
        lock_readonly(target)
        return target
