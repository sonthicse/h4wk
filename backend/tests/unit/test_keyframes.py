import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest

from h4wk.media.keyframes import Keyframe, KeyframeSettings, extract_keyframes, select_keyframes

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
    settings = KeyframeSettings(phash_threshold=64, tile_threshold=255)
    frames = extract_keyframes(tmp_path, settings)
    assert [(frame.t, frame.scene) for frame in frames] == [(0, 1), (3.25, 2)]
    assert set((tmp_path / "frames").glob("*.jpg")) == {tmp_path / frame.file for frame in frames}


def _frame(n: int, t: float, hash: str = "0" * 16) -> Keyframe:
    return Keyframe(file=f"frames/{n:06d}.jpg", t=t, scene=1, hash=hash)


def test_select_drops_frames_that_look_like_any_kept_frame():
    frames = [_frame(i, i / 2) for i in range(5)]
    a, b = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    # A A B A B: cảnh quay lại A, B vẫn bị bỏ vì giống một keyframe đã giữ.
    vectors = np.stack([a, a * 0.99 + b * 0.14, b, a, b])
    kept = select_keyframes(frames, {}, vectors)
    assert [f.file for f in kept] == [frames[0].file, frames[2].file]


def test_select_keeps_new_text_but_not_ocr_variants():
    frames = [_frame(i, i / 2) for i in range(5)]
    vectors = np.ones((5, 2)) / np.sqrt(2)
    texts = {
        frames[0].file: [("CHÍNH QUYỀN TÔ LÂM", 0.95)],
        frames[1].file: [("CHĨNH DUYỀN TỔ LÂM", 0.9)],  # OCR đọc lệch: không phải chữ mới
        frames[2].file: [("Nguyễn Đắc Vinh", 0.92), ("CHÍNH QUYỀN TÔ LÂM", 0.95)],
        frames[3].file: [("Nguyễn Đắc Vinh", 0.3)],  # score thấp: bỏ qua
        frames[4].file: [("abc", 0.99)],  # quá ngắn
    }
    kept = select_keyframes(frames, texts, vectors)
    assert [f.file for f in kept] == [frames[0].file, frames[2].file]


def test_select_without_vectors_drops_only_identical_hashes():
    frames = [_frame(0, 0), _frame(1, 0.5), _frame(2, 1, "f" * 16)]
    kept = select_keyframes(frames, {}, None)
    assert [f.file for f in kept] == [frames[0].file, frames[2].file]
