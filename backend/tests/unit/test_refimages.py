"""T40: khớp ảnh mẫu, dùng embedder giả (không cần torch)."""

from pathlib import Path

import cv2
import numpy as np
import pytest

from h4wk.analysis import refimages
from h4wk.media.timeline import Frame, FrameOcr, Segment, Timeline


class ColorEmbedder:
    """Embedding giả: màu trung bình đã chuẩn hoá L2 (đủ để phân biệt ô đỏ với ô xanh)."""

    name = "fake-color"

    def __init__(self):
        self.calls = 0  # số ảnh đã embed

    def embed(self, images):
        self.calls += len(images)
        vectors = np.array([img.reshape(-1, 3).mean(axis=0) for img in images], dtype=np.float64)
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


def _write(path: Path, rgb: np.ndarray) -> Path:
    assert cv2.imwrite(str(path), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return path


@pytest.fixture
def scene(tmp_path):
    ref = np.zeros((64, 64, 3), np.uint8)
    ref[...] = (255, 0, 0)  # ảnh mẫu toàn đỏ
    frame = np.zeros((360, 640, 3), np.uint8)
    frame[...] = (0, 0, 255)  # nền xanh
    frame[0:180, 320:640] = (255, 0, 0)  # ô trên phải của lưới 2×2 là đỏ
    blank = np.zeros((360, 640, 3), np.uint8)
    blank[...] = (0, 0, 255)
    return {
        "refs": {"e_01": [_write(tmp_path / "ref.png", ref)]},
        "images": [
            ("frames/000001.jpg", _write(tmp_path / "f1.png", frame)),
            ("frames/000002.jpg", _write(tmp_path / "f2.png", blank)),
        ],
    }


def test_grid_crops_cover_full_2x2_and_3x3():
    crops = refimages.grid_crops(np.zeros((360, 640, 3), np.uint8))
    assert len(crops) == 1 + 4 + 9
    assert crops[0][0] == (0, 0, 640, 360)
    assert crops[1][0] == (0, 0, 320, 180) and crops[4][0] == (320, 180, 320, 180)
    assert crops[-1][0] == (426, 240, 214, 120)
    assert all(c.shape[:2] == (h, w) for (_, _, w, h), c in crops)


def test_keeps_only_best_crop_per_image_and_entity(scene):
    hits = refimages.match_refs(scene["images"], scene["refs"], ColorEmbedder(), 0.9)
    assert [(e, f, bbox) for e, f, bbox, _ in hits] == [
        ("e_01", "frames/000001.jpg", (320, 0, 320, 180))
    ]
    assert hits[0][3] == pytest.approx(1.0)


def test_threshold_comes_from_argument_else_default(scene):
    assert refimages.match_refs(scene["images"], scene["refs"], ColorEmbedder(), 1.01) == []
    default = refimages.match_refs(scene["images"], scene["refs"], ColorEmbedder())
    assert [h[1] for h in default] == ["frames/000001.jpg"]  # blank có cosine 0 < mặc định


def test_embeddings_cache_is_reused(scene, tmp_path):
    cache = tmp_path / "derived" / "embeddings.npz"
    first = ColorEmbedder()
    refimages.match_refs(scene["images"], scene["refs"], first, 0.9, cache)
    assert first.calls == 1 + 2 * 14 and cache.is_file()
    second = ColorEmbedder()
    refimages.match_refs(scene["images"], scene["refs"], second, 0.9, cache)
    assert second.calls == 1  # chỉ embed lại ảnh mẫu
    other = ColorEmbedder()
    other.name = "other-model"
    refimages.match_refs(scene["images"], scene["refs"], other, 0.9, cache)
    assert other.calls == 1 + 2 * 14  # đổi model thì bỏ cache


def test_missing_refs_or_unreadable_images_are_skipped(scene, tmp_path):
    assert refimages.match_refs(scene["images"], {}, ColorEmbedder(), 0.5) == []
    images = [*scene["images"], ("frames/missing.jpg", tmp_path / "missing.jpg")]
    hits = refimages.match_refs(images, scene["refs"], ColorEmbedder(), 0.9)
    assert [h[1] for h in hits] == ["frames/000001.jpg"]  # ảnh không đọc được bị bỏ qua


def test_to_hits_assigns_segment_by_timeline():
    timeline = Timeline(
        schema="h4wk.timeline/1",
        video_id="v",
        capture="20261118T160000",
        segments=[
            Segment(
                id="seg_0001",
                start=0,
                end=10,
                frames=[Frame(frame="frames/000001.jpg", t=3)],
            ),
            Segment(
                id="seg_0002",
                start=10,
                end=20,
                ocr=[FrameOcr(frame="frames/000002.jpg", t=12, text="x", bbox=(0, 0, 1, 1))],
            ),
        ],
    )
    box = (0, 0, 10, 10)
    matches = [
        ("e_01", "frames/000001.jpg", box, 0.9),
        ("e_01", "frames/000002.jpg", box, 0.8),
        ("e_01", "frames/000003.jpg", box, 0.8),
        ("e_01", "frames/000004.jpg", box, 0.8),
        ("e_01", "thumb.jpg", box, 0.8),
    ]
    times = {"frames/000003.jpg": 15.0, "frames/000004.jpg": 99.0}
    hits = refimages.to_hits(matches, timeline, times)
    assert [h.segment_id for h in hits] == ["seg_0001", "seg_0002", "seg_0002", None, None]
    assert all(h.via == "ref_image" and h.frame and h.score for h in hits)
