from pathlib import Path
from unittest.mock import Mock

import pytest

from h4wk.analysis import faces
from h4wk.jobs import pipeline
from h4wk.media.timeline import Segment, Timeline

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/faces"


def test_match_faces_does_not_store_features(monkeypatch, tmp_path):
    recognizer = Mock()
    recognizer.match.side_effect = [0.95, 0.1]
    monkeypatch.setattr(faces, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(faces, "_models", lambda _: (Mock(), recognizer))
    monkeypatch.setattr(faces, "_features", lambda *args: [((1, 2, 3, 4), object())])
    before = set(tmp_path.iterdir())
    assert faces.match_faces([("same", tmp_path), ("other", tmp_path)], {"ref": [tmp_path]}) == [
        ("ref", "same", (1, 2, 3, 4), 0.95)
    ]
    assert set(tmp_path.iterdir()) == before


def test_pipeline_without_face_refs_does_nothing(monkeypatch, tmp_path):
    """Không có ảnh khuôn mặt mẫu thì không chạy khớp khuôn mặt (cách để tắt bước này)."""
    monkeypatch.setattr(pipeline, "load_entities", lambda: [Mock(id="ref")])
    monkeypatch.setattr(pipeline, "refs_dir", lambda *_: tmp_path)  # thư mục trống
    matcher = Mock()
    monkeypatch.setattr(faces, "match_faces", matcher)
    pipeline._faces(None, tmp_path, tmp_path, [], [], None)
    matcher.assert_not_called()
    assert not (tmp_path / "face_hits.json").exists()


def test_pipeline_face_error_is_audited(monkeypatch, tmp_path):
    ref = tmp_path / "0123456789abcdef.jpg"
    ref.touch()
    target = tmp_path / "face_hits.json"
    target.write_text("[]", encoding="utf-8")
    job = Mock(id="job_test", trigger="manual")
    log = Mock()
    matcher = Mock(side_effect=OSError("Model download failed"))
    monkeypatch.setattr(pipeline, "load_entities", lambda: [Mock(id="ref")])
    monkeypatch.setattr(pipeline, "refs_dir", lambda *_: tmp_path)
    monkeypatch.setattr(faces, "match_faces", matcher)
    monkeypatch.setattr(pipeline.audit, "log", log)

    pipeline._faces(job, tmp_path, tmp_path, [], [ref.name], None)

    matcher.assert_called_once_with([(ref.name, ref)], {"ref": [ref]})
    log.assert_called_once_with(
        "manual", "media.face", "job_test", {"error": "Model download failed"}, status="error"
    )
    assert not target.exists()


def test_to_hits_marks_face_and_preserves_location():
    frame = "frames/000001.jpg"
    timeline = Timeline(
        schema="h4wk.timeline/1",
        video_id="demo",
        capture="20261118T160000",
        segments=[Segment(id="seg_0001", start=1, end=3)],
    )
    (hit,) = faces.to_hits([("ent_0001", frame, (1, 2, 3, 4), 0.91)], timeline, {frame: 2})
    assert (hit.via, hit.segment_id, hit.frame) == ("face", "seg_0001", frame)
    assert (hit.bbox, hit.score) == ((1, 2, 3, 4), 0.91)


@pytest.mark.live
def test_opencv_faces(monkeypatch, tmp_path):
    import cv2

    monkeypatch.setattr(faces, "data_dir", lambda: tmp_path)
    ref = FIXTURES / "astronaut.png"
    bright = tmp_path / "bright.jpg"
    assert cv2.imwrite(str(bright), cv2.convertScaleAbs(cv2.imread(str(ref)), alpha=0.85, beta=15))
    hits = faces.match_faces(
        [("same", bright), ("other", FIXTURES / "grace_hopper.jpg")], {"ref": [ref]}
    )
    assert [(entity, name) for entity, name, _, _ in hits] == [("ref", "same")]
    assert {p.name for p in (tmp_path / "models").iterdir()} == {m[1] for m in faces.MODELS}
