from pathlib import Path
from unittest.mock import Mock

import pytest

from h4wk.analysis import faces
from h4wk.core.config_models import AnalysisConfig, FaceSettings
from h4wk.jobs import pipeline

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


def test_pipeline_disabled(monkeypatch, tmp_path):
    monkeypatch.setattr(
        pipeline, "_analysis_config", lambda: AnalysisConfig(face=FaceSettings(enabled=False))
    )
    matcher = Mock()
    monkeypatch.setattr(faces, "match_faces", matcher)
    pipeline._faces(None, tmp_path, tmp_path, [], [], None)
    matcher.assert_not_called()
    assert not (tmp_path / "face_hits.json").exists()


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
