"""T9: thu đủ một video thật bằng yt-dlp (gọi mạng, chạy tay: uv run pytest -m live -k ytdlp)."""

import os
from pathlib import Path

import pytest

from h4wk.collectors.models import Cap, CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator, Settings
from h4wk.collectors.providers.ytdlp import YtDlpCollector
from h4wk.collectors.targets import parse_target
from h4wk.evidence.models import Manifest, Trigger
from h4wk.evidence.verify import FileStatus, verify

# Video tiếng Việt công khai, khoảng 7 phút, có phụ đề tự động (đã dùng ở spike T2).
VIDEO = "https://www.youtube.com/watch?v=oAFNS8b7br0"


@pytest.mark.live
def test_ytdlp_collects_full_video(data_dir: Path) -> None:
    orch = Orchestrator(
        {"ytdlp": YtDlpCollector()},
        Settings(priority={c: ["ytdlp"] for c in Cap}),
        case_dir=data_dir / "cases" / "live",
    )
    cap = orch.collect(
        parse_target(VIDEO),
        CollectLevel.FULL,
        collector="user:test",
        trigger=Trigger(type="manual"),
    )
    try:
        m = Manifest.model_validate_json((cap / "manifest.json").read_text("utf-8"))
        n = Normalized.model_validate_json((cap / "normalized.json").read_text("utf-8"))
        assert [c.status for c in m.sources] == ["ok"] * 5, m.sources
        assert n.video and n.video.id == "oAFNS8b7br0"
        assert any(t.lang == "vi" and t.segments for t in n.transcripts)
        assert n.media and (n.media[0].height or 0) >= 360
        assert any(t.name == "maxres" for t in n.thumbnails)
        assert all(r.status == FileStatus.OK for r in verify(cap))
    finally:
        for root, dirs, _ in os.walk(cap):
            for d in dirs:
                os.chmod(Path(root) / d, 0o755)
        os.chmod(cap, 0o755)
