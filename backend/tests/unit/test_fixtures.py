"""Bản thu mẫu (T44): mọi file JSON validate theo C1–C4 và SHA-256 trong manifest khớp."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from h4wk.analysis.models import EntityHit, Finding, SourceKind
from h4wk.collectors.models import Normalized
from h4wk.evidence.models import Manifest
from h4wk.media.timeline import Timeline

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
VIDEO_ID = "h4wkDemo001"
CAPTURE = "20261118T160000"
RUN_ID = "r_20261118T160500"
VIDEO_DIR = FIXTURES / "captures" / VIDEO_ID
CAPTURE_DIR = VIDEO_DIR / "captures" / CAPTURE
DERIVED_DIR = VIDEO_DIR / "derived" / CAPTURE
RUN_DIR = DERIVED_DIR / "analysis" / RUN_ID
REFS_DIR = FIXTURES / "refs" / "e_01"


def _json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def manifest() -> Manifest:
    return Manifest.model_validate(_json(CAPTURE_DIR / "manifest.json"))


@pytest.fixture(scope="module")
def timeline() -> Timeline:
    return Timeline.model_validate(_json(DERIVED_DIR / "timeline.json"))


@pytest.fixture(scope="module")
def hits() -> list[EntityHit]:
    return TypeAdapter(list[EntityHit]).validate_python(_json(RUN_DIR / "hits.json"))


@pytest.fixture(scope="module")
def findings() -> list[Finding]:
    return TypeAdapter(list[Finding]).validate_python(_json(RUN_DIR / "findings.json"))


def test_manifest_hashes_match_every_file(manifest: Manifest) -> None:
    on_disk = {
        p.relative_to(CAPTURE_DIR).as_posix()
        for p in CAPTURE_DIR.rglob("*")
        if p.is_file() and p.name != "manifest.json"
    }
    # Không thiếu file, không có file lạ.
    assert on_disk == set(manifest.files)
    for rel, entry in manifest.files.items():
        path = CAPTURE_DIR / rel
        assert entry.bytes == path.stat().st_size, rel
        assert entry.sha256 == _sha256(path), rel


def test_normalized_is_valid_and_points_to_real_files() -> None:
    n = Normalized.model_validate(_json(CAPTURE_DIR / "normalized.json"))
    assert n.video is not None and n.video.id == VIDEO_ID
    assert any(t.lang == "vi" and t.segments for t in n.transcripts)
    for f in [m.file for m in n.media] + [t.file for t in n.thumbnails if t.file]:
        assert (CAPTURE_DIR / f).is_file(), f


def test_timeline_matches_capture(timeline: Timeline, manifest: Manifest) -> None:
    assert timeline.video_id == VIDEO_ID and timeline.capture == CAPTURE
    video = next(rel for rel in manifest.files if rel.endswith(".mp4"))
    assert timeline.source_video_sha256 == manifest.files[video].sha256
    for seg in timeline.segments:
        for item in [*seg.ocr, *seg.visual]:
            assert (DERIVED_DIR / item.frame).is_file(), item.frame


def test_hits_cover_every_kind_of_sign(hits: list[EntityHit], timeline: Timeline) -> None:
    assert {h.via for h in hits} >= {"speech", "ocr", "face", "ref_image", "comment"}
    seg_ids = {s.id for s in timeline.segments}
    for h in hits:
        assert h.segment_id is None or h.segment_id in seg_ids
        assert h.frame is None or (DERIVED_DIR / h.frame).is_file(), h.frame


def test_findings_match_run_and_capture(findings: list[Finding], timeline: Timeline) -> None:
    assert len({f.id for f in findings}) == len(findings)
    for f in findings:
        assert (f.run_id, f.video_id, f.capture) == (RUN_ID, VIDEO_ID, CAPTURE)
    # Kịch bản T44: có nghi vấn hình ảnh ở đoạn không ai nhắc tên.
    speech_by_seg = {s.id: s.speech for s in timeline.segments}
    visual = [f for f in findings if f.source_kind == SourceKind.VISUAL]
    assert visual
    assert all("Mẫu" not in speech_by_seg[f.segment_id] for f in visual if f.segment_id)


def test_reference_images_exist() -> None:
    assert list((REFS_DIR / "face").glob("*.png"))
    assert list((REFS_DIR / "image").glob("*.png"))
