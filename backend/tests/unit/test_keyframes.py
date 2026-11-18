import json
import shutil
from pathlib import Path

import cv2
import pytest

from h4wk.core.config_models import AnalysisConfig, KeyframeSettings, load_toml
from h4wk.media.keyframes import extract_keyframes

CLIPS = Path(__file__).parents[1] / "fixtures" / "clips"


def setup_proxy(tmp_path, name):
    shutil.copyfile(CLIPS / name, tmp_path / "proxy_480p.mp4")


@pytest.mark.parametrize(
    "settings",
    [
        KeyframeSettings(),
        KeyframeSettings(phash_threshold=64),
        KeyframeSettings(phash_threshold=0, tile_threshold=255),
    ],
)
def test_one_second_corner_text_and_scene_cut(tmp_path, settings):
    setup_proxy(tmp_path, "corner-text.mp4")
    frames = extract_keyframes(tmp_path, settings)
    text = next(frame for frame in frames if 1 <= frame.t < 2)
    jpeg = cv2.imread(str(tmp_path / text.file))
    assert jpeg.shape == (360, 640, 3)
    assert jpeg[:35, :100].max() > 180
    assert jpeg[35:].max() < 10
    assert {frame.scene for frame in frames} == {1, 2}
    assert next(frame.t for frame in frames if frame.scene == 2) == pytest.approx(3.25)
    assert all(len(frame.hash) == 16 for frame in frames)
    index = json.loads((tmp_path / "frames/index.json").read_bytes())
    assert index["frames"] == [frame.model_dump() for frame in frames]


def test_static_two_minutes_and_cached_retry(tmp_path, monkeypatch):
    from h4wk.media import keyframes

    setup_proxy(tmp_path, "static-120s.mp4")
    frames = extract_keyframes(tmp_path)
    assert 1 <= len(frames) <= 3
    path = tmp_path / frames[0].file
    assert frames[0].t == 0 and path.is_file()
    with monkeypatch.context() as patch:
        patch.setattr(keyframes, "detect", lambda *args, **kwargs: pytest.fail("decoded twice"))
        assert extract_keyframes(tmp_path) == frames
    path.unlink()
    assert extract_keyframes(tmp_path) == frames
    assert cv2.imread(str(path)) is not None


def test_change_thresholds_keeps_scene_representatives(tmp_path):
    setup_proxy(tmp_path, "corner-text.mp4")
    assert len(extract_keyframes(tmp_path)) > 2
    config = tmp_path / "analysis.toml"
    config.write_text("[keyframes]\nphash_threshold=64\ntile_threshold=255\n")
    frames = extract_keyframes(tmp_path, load_toml(config, AnalysisConfig).keyframes)
    assert [(frame.t, frame.scene) for frame in frames] == [(0, 1), (3.25, 2)]
    assert set((tmp_path / "frames").glob("*.jpg")) == {tmp_path / frame.file for frame in frames}
