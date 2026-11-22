from pathlib import Path

import pytest

from h4wk.collectors.models import Cap, CollectLevel, Normalized, TranscriptKind
from h4wk.collectors.orchestrator import Orchestrator, Settings
from h4wk.collectors.providers import supadata
from h4wk.collectors.providers.supadata import SupadataCollector
from h4wk.collectors.targets import parse_target
from h4wk.core import secrets
from h4wk.evidence.models import Manifest, SourceStatus, Trigger
from h4wk.evidence.verify import FileStatus, verify

VIDEO = "https://www.youtube.com/watch?v=oAFNS8b7br0"
SHORT = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


@pytest.fixture(autouse=True)
def _need_key() -> None:
    if not secrets.get("SUPADATA_API_KEY"):
        pytest.skip("Cần SUPADATA_API_KEY để gọi Supadata")


@pytest.mark.live
def test_supadata_native_transcript(data_dir: Path) -> None:
    orch = Orchestrator(
        {"supadata": SupadataCollector()},
        Settings(priority={c: ["supadata"] for c in Cap}),
        root=data_dir,
    )
    cap = orch.collect(
        parse_target(VIDEO),
        CollectLevel.TEXT,
        collector="user:test",
        trigger=Trigger(type="manual"),
    )
    m = Manifest.model_validate_json((cap / "manifest.json").read_text("utf-8"))
    n = Normalized.model_validate_json((cap / "normalized.json").read_text("utf-8"))
    status = {c.what: c.status for c in m.sources if c.provider}
    assert status[Cap.VIDEO_METADATA] == SourceStatus.OK, m.sources
    assert status[Cap.TRANSCRIPTS] == SourceStatus.OK, m.sources
    t = n.transcripts[0]
    assert t.kind == TranscriptKind.SUPADATA_AI and t.lang.startswith("vi")
    assert t.segments and all(s.end >= s.start for s in t.segments)
    assert n.video and n.video.channel_id.startswith("UC")
    call = next(c for c in m.sources if c.what == Cap.TRANSCRIPTS and c.provider)
    assert call.cost and call.cost.credits >= 1
    assert all(r.status == FileStatus.OK for r in verify(cap))


@pytest.mark.live
def test_supadata_generate_transcript(tmp_path: Path) -> None:
    res = SupadataCollector().fetch(Cap.TRANSCRIPTS, parse_target(SHORT), tmp_path)
    assert res.normalized.transcripts and res.normalized.transcripts[0].segments
    assert res.cost.credits >= 2
    assert list(tmp_path.glob("*.transcript.generate.json"))


@pytest.mark.live
def test_supadata_credits_usage() -> None:
    supadata._me_cache.clear()
    u = supadata.credits_usage()
    assert u is not None and u.limit > 0 and 0 <= u.used <= u.limit
