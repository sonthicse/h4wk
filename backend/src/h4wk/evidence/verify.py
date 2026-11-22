"""Kiểm tra toàn vẹn một bản thu theo manifest."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from h4wk.evidence.models import Manifest
from h4wk.evidence.writer import sha256_file


class FileStatus(StrEnum):
    OK = "OK"
    FAIL = "FAIL"  # SHA-256 hoặc kích thước khác manifest
    MISSING = "missing"
    UNEXPECTED = "unexpected"  # có trên đĩa nhưng không có trong manifest


@dataclass(frozen=True)
class FileCheck:
    path: str
    status: FileStatus


def verify(capture_dir: Path) -> list[FileCheck]:
    """Kết quả từng file, sắp theo đường dẫn. manifest.json không tự kiểm chính nó."""
    manifest = Manifest.model_validate_json(
        (capture_dir / "manifest.json").read_text(encoding="utf-8")
    )
    on_disk = {
        p.relative_to(capture_dir).as_posix() for p in capture_dir.rglob("*") if p.is_file()
    } - {"manifest.json"}
    results = []
    for rel in sorted(set(manifest.files) | on_disk):
        entry = manifest.files.get(rel)
        if entry is None:
            status = FileStatus.UNEXPECTED
        elif rel not in on_disk:
            status = FileStatus.MISSING
        else:
            path = capture_dir / rel
            same = path.stat().st_size == entry.bytes and sha256_file(path) == entry.sha256
            status = FileStatus.OK if same else FileStatus.FAIL
        results.append(FileCheck(rel, status))
    return results
