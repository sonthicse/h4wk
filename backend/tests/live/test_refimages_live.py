"""Khớp ảnh mẫu bằng DINOv2 thật (GPU nếu có). Lần đầu tải trọng số từ Hugging Face.

Chạy: `uv run --extra match pytest -m live tests/live/test_refimages_live.py -s`."""

from pathlib import Path

import cv2
import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from h4wk.analysis import refimages  # noqa: E402

pytestmark = pytest.mark.live
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REF = FIXTURES / "refs/e_01/image/ref_01.png"
FRAMES = FIXTURES / "captures/h4wkDemo001/derived/20261118T160000/frames"


@pytest.fixture(scope="module")
def embedder():
    return refimages.DinoEmbedder()


def _rgb(path: Path) -> np.ndarray:
    return cv2.cvtColor(cv2.imread(str(path)), cv2.COLOR_BGR2RGB)


def _best(embedder, image: np.ndarray, ref_vector: np.ndarray) -> float:
    vectors = embedder.embed([crop for _, crop in refimages.grid_crops(image)])
    return float((vectors @ ref_vector.T).max())


def test_ref_image_variants_match_and_other_frames_do_not(embedder, tmp_path):
    ref = _rgb(REF)
    height, width = ref.shape[:2]
    ref_vector = embedder.embed([ref])
    hsv = cv2.cvtColor(ref, cv2.COLOR_RGB2HSV)
    desaturated = hsv.copy()
    desaturated[..., 1] //= 2
    shifted = hsv.copy()
    shifted[..., 0] = (shifted[..., 0].astype(int) + 30) % 180
    composite = _rgb(FRAMES / "000015.jpg")
    composite[10:170, -170:-10] = cv2.resize(ref, (160, 160))
    positives = {
        "cắt nửa": ref[:, : width // 2],
        "cắt 10% mỗi cạnh": ref[height // 10 : -height // 10, width // 10 : -width // 10],
        "giảm bão hoà 50%": cv2.cvtColor(desaturated, cv2.COLOR_HSV2RGB),
        "đổi hue": cv2.cvtColor(shifted.astype(np.uint8), cv2.COLOR_HSV2RGB),
        "ghép vào góc khung": composite,
        "khung T44 có ảnh mẫu cắt và đổi màu": _rgb(FRAMES / "000032.jpg"),
    }
    negatives = {"khung 000015": FRAMES / "000015.jpg", "khung 000025": FRAMES / "000025.jpg"}
    threshold = refimages.DEFAULT_THRESHOLD
    for name, image in positives.items():
        score = _best(embedder, image, ref_vector)
        print(f"{name}: {score:.3f}")
        assert score >= threshold, name
    for name, path in negatives.items():
        score = _best(embedder, _rgb(path), ref_vector)
        print(f"{name}: {score:.3f}")
        assert score < threshold, name


def test_match_refs_on_sample_capture(embedder, tmp_path):
    images = [(f"frames/{p.name}", p) for p in sorted(FRAMES.glob("*.jpg"))]
    hits = refimages.match_refs(images, {"e_01": [REF]}, embedder, cache=tmp_path / "e.npz")
    assert {frame for _, frame, _, _ in hits} == {"frames/000032.jpg", "frames/000034.jpg"}
