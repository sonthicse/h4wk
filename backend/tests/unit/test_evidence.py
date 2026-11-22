"""T5: ghi bản thu, manifest, verify."""

import os
import stat
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

import pytest

from h4wk.collectors.models import Normalized
from h4wk.core.types import VN_TZ, Cap
from h4wk.evidence.models import Manifest, SourceCall, SourceStatus, Trigger
from h4wk.evidence.verify import FileStatus, verify
from h4wk.evidence.writer import CaptureWriter

FIXTURE_CAPTURE = (
    Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001/captures/20261118T160000"
)
T1 = datetime(2026, 11, 19, 9, 0, 0, tzinfo=VN_TZ)
T2 = datetime(2026, 11, 19, 9, 30, 0, tzinfo=VN_TZ)


def unlock(path: Path) -> None:
    """Mở khoá chỉ đọc để test sửa hoặc dọn bản thu."""
    for root, dirs, files in os.walk(path):
        os.chmod(root, 0o755)
        for d in dirs:
            os.chmod(Path(root) / d, 0o755)
        for f in files:
            os.chmod(Path(root) / f, 0o644)


@pytest.fixture
def captures_dir(tmp_path: Path) -> Iterator[Path]:
    d = tmp_path / "videos" / "abc123" / "captures"
    yield d
    if d.exists():
        unlock(d)


def _normalized() -> Normalized:
    return Normalized.model_validate(
        {
            "schema": "h4wk.normalized/1",
            "video": {"id": "abc123", "channel_id": "UCx", "title": "Tiêu đề có dấu"},
        }
    )


def _calls() -> list[SourceCall]:
    return [
        SourceCall(provider="ytdlp", what=Cap.VIDEO_METADATA, status=SourceStatus.OK),
        SourceCall(
            provider="youtube_api", what=Cap.COMMENTS, status=SourceStatus.BLOCKED, error="403"
        ),
    ]


def _capture(captures_dir: Path, now: datetime) -> Path:
    w = CaptureWriter(
        captures_dir,
        source_url="https://www.youtube.com/watch?v=abc123",
        collector="user:thi",
        trigger=Trigger(type="manual"),
        level="full",
        now=now,
    )
    (w.workdir("ytdlp") / "abc123.info.json").write_text('{"id": "abc123"}', encoding="utf-8")
    (w.workdir("ytdlp") / "video.mp4").write_bytes(b"\x00\x01video")
    return w.finalize(_normalized(), _calls())


def test_finalize_writes_locked_capture(captures_dir: Path) -> None:
    cap = _capture(captures_dir, T1)
    assert cap == captures_dir / "20261119T090000"
    m = Manifest.model_validate_json((cap / "manifest.json").read_text(encoding="utf-8"))
    assert set(m.files) == {
        "normalized.json",
        "sources/ytdlp/abc123.info.json",
        "sources/ytdlp/video.mp4",
    }
    assert m.collected_at == T1 and m.previous_capture is None
    assert [c.status for c in m.sources] == ["ok", "blocked"]  # có cả lần gọi thất bại
    assert m.tool_version.startswith("h4wk ")
    # Không còn thư mục tạm, và cả file lẫn thư mục đều chỉ đọc.
    assert [p.name for p in captures_dir.iterdir()] == ["20261119T090000"]
    for p in [cap, *cap.rglob("*")]:
        assert not p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH), p
    assert all(r.status == FileStatus.OK for r in verify(cap))


def test_verify_reports_fail_for_one_changed_byte(captures_dir: Path) -> None:
    cap = _capture(captures_dir, T1)
    unlock(cap)
    video = cap / "sources/ytdlp/video.mp4"
    data = bytearray(video.read_bytes())
    data[0] ^= 1
    video.write_bytes(bytes(data))
    bad = {r.path: r.status for r in verify(cap) if r.status != FileStatus.OK}
    assert bad == {"sources/ytdlp/video.mp4": FileStatus.FAIL}


def test_verify_reports_missing_and_unexpected(captures_dir: Path) -> None:
    cap = _capture(captures_dir, T1)
    unlock(cap)
    (cap / "sources/ytdlp/abc123.info.json").unlink()
    (cap / "sources/ytdlp/extra.txt").write_text("lạ", encoding="utf-8")
    bad = {r.path: r.status for r in verify(cap) if r.status != FileStatus.OK}
    assert bad == {
        "sources/ytdlp/abc123.info.json": FileStatus.MISSING,
        "sources/ytdlp/extra.txt": FileStatus.UNEXPECTED,
    }


def test_recapture_points_to_previous(captures_dir: Path) -> None:
    _capture(captures_dir, T1)
    cap2 = _capture(captures_dir, T2)
    m = Manifest.model_validate_json((cap2 / "manifest.json").read_text(encoding="utf-8"))
    assert m.previous_capture == "20261119T090000"


def test_failed_finalize_leaves_no_capture(captures_dir: Path) -> None:
    _capture(captures_dir, T1)
    with pytest.raises(FileExistsError):
        _capture(captures_dir, T1)  # trùng mốc giờ
    assert [p.name for p in captures_dir.iterdir()] == ["20261119T090000"]


def test_sample_capture_verifies_ok() -> None:
    assert all(r.status == FileStatus.OK for r in verify(FIXTURE_CAPTURE))
