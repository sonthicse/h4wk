"""Khớp ảnh mẫu bằng embedding ảnh (DINOv2 ViT-S/14): bắt ảnh bị cắt, ghép, đổi màu.

Mỗi ảnh (keyframe, thumbnail) được cắt thành khung đầy đủ cùng lưới 2×2 và 3×3, mỗi ô
được so cosine với embedding của các ảnh mẫu.

DEFAULT_THRESHOLD đã hiệu chỉnh bằng test model thật (H4WK_TEST_DINO=1) trên ảnh mẫu
`tests/fixtures/refs/e_01/image/ref_01.png` và bản thu mẫu T44 (cosine tốt nhất theo ô):
  - khớp: nguyên bản 1,000; hue +30 0,971; giảm bão hoà 50% 0,941; cắt mỗi cạnh 10% 0,906;
    khung T44 có ảnh mẫu cắt và đổi màu (000032, 000034) 0,898; cắt nửa ảnh 0,834;
    ảnh mẫu thu nhỏ ghép vào góc khung T44 0,921;
  - không khớp: khung T44 không có ảnh mẫu (000015 0,486; 000025 0,549).
Ngưỡng 0,75 nằm giữa hai nhóm. Mới có hai khung âm tính nên ngưỡng cần kiểm lại trên video thật.
"""

import hashlib
import logging
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

import cv2
import numpy as np

from h4wk.analysis.models import EntityHit
from h4wk.media.timeline import Timeline

logger = logging.getLogger(__name__)

MODEL_ID = "facebook/dinov2-small"
MODEL_REVISION = "ed25f3a"
DEFAULT_THRESHOLD = 0.75


class Embedder(Protocol):
    name: str

    def embed(self, images: list[np.ndarray]) -> np.ndarray:
        """Ảnh RGB uint8 (h, w, 3) -> ma trận (n, d) đã chuẩn hoá L2."""
        ...


class DinoEmbedder:
    """Nạp lười model một lần cho mỗi worker (như SttWorker). Bắt buộc có GPU NVIDIA (CUDA)."""

    name = f"{MODEL_ID}@{MODEL_REVISION}"

    def __init__(self) -> None:
        self._model = None
        self._processor = None
        self._device = "cpu"

    def _load(self) -> None:
        import torch
        from transformers import AutoImageProcessor, AutoModel

        if not torch.cuda.is_available():
            raise RuntimeError("an NVIDIA GPU with CUDA is required for reference image matching")
        self._device = "cuda"
        self._processor = AutoImageProcessor.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
        self._model = AutoModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION)
        self._model.to(self._device).eval()
        logger.info("Đã nạp model ảnh mẫu %s trên %s", self.name, self._device)

    def embed(self, images: list[np.ndarray]) -> np.ndarray:
        import torch

        if self._model is None:
            self._load()
        out = []
        for start in range(0, len(images), 32):
            batch = self._processor(images=images[start : start + 32], return_tensors="pt")
            with torch.no_grad():
                hidden = self._model(**batch.to(self._device)).last_hidden_state[:, 0]
            out.append(torch.nn.functional.normalize(hidden, dim=1).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 384), dtype=np.float32)


def grid_crops(image: np.ndarray) -> list[tuple[tuple[int, int, int, int], np.ndarray]]:
    """Khung đầy đủ cộng lưới 2×2 và 3×3; bbox [x, y, w, h] theo pixel của ảnh nguồn."""
    height, width = image.shape[:2]
    crops = [((0, 0, width, height), image)]
    for n in (2, 3):
        for row in range(n):
            for col in range(n):
                x0, x1 = col * width // n, (col + 1) * width // n
                y0, y1 = row * height // n, (row + 1) * height // n
                crops.append(((x0, y0, x1 - x0, y1 - y0), image[y0:y1, x0:x1]))
    return crops


def _read(path: Path) -> np.ndarray | None:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    return None if image is None else cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _load_cache(path: Path | None, embedder: Embedder) -> dict[str, np.ndarray]:
    if path is None or not path.is_file():
        return {}
    try:
        with np.load(path) as data:
            if str(data["__model__"]) != embedder.name:
                return {}
            return {k: data[k] for k in data.files if k != "__model__"}
    except (OSError, ValueError, KeyError):
        return {}


def match_refs(
    images: Sequence[tuple[str, Path]],
    refs: dict[str, list[Path]],
    embedder: Embedder,
    threshold: float | None = None,
    cache: Path | None = None,
) -> list[tuple[str, str, tuple[int, int, int, int], float]]:
    """Trả (entity, file, bbox, score). Mỗi cặp (ảnh, đối tượng) chỉ giữ ô điểm cao nhất
    vượt ngưỡng. Embedding của ô cắt lưu ở `cache` (npz, khoá theo sha256 của ảnh)."""
    limit = DEFAULT_THRESHOLD if threshold is None else threshold
    ref_vectors: dict[str, np.ndarray] = {}
    for entity, paths in refs.items():
        arrays = [a for a in (_read(p) for p in paths) if a is not None]
        if arrays:
            ref_vectors[entity] = embedder.embed(arrays)
    if not ref_vectors:
        return []

    cached = _load_cache(cache, embedder)
    fresh: dict[str, np.ndarray] = {}
    dirty = False
    hits = []
    for file, path in images:
        array = _read(path)
        if array is None:
            logger.warning("Cannot read image %s", path)
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        crops = grid_crops(array)
        vectors = cached.get(digest)
        if vectors is None or len(vectors) != len(crops):
            vectors = embedder.embed([crop for _, crop in crops])
            dirty = True
        fresh[digest] = vectors
        for entity, refs_matrix in ref_vectors.items():
            scores = (vectors @ refs_matrix.T).max(axis=1)
            best = int(scores.argmax())
            if scores[best] >= limit:
                hits.append((entity, file, crops[best][0], float(scores[best])))
    if cache is not None and dirty:
        cache.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache.with_suffix(".tmp.npz")
        np.savez(tmp, __model__=np.array(embedder.name), **fresh)
        tmp.replace(cache)
    return hits


def to_hits(
    matches: list[tuple[str, str, tuple[int, int, int, int], float]],
    timeline: Timeline,
    frame_times: dict[str, float],
) -> list[EntityHit]:
    """Đổi kết quả khớp thành EntityHit (via ref_image), gán segment_id theo timeline:
    ưu tiên segment chứa khung trong frames hoặc ocr, sau đó segment có start <= t <= end.
    Thumbnail (không có thời điểm) không có segment_id.

    Giới hạn: khung khớp ảnh mẫu mà không thuộc segment nào (ngoài lời nói, không có keyframe
    hay OCR) chỉ nằm trong hits.json, không được gửi cho Jev."""
    owner: dict[str, str] = {}
    for segment in timeline.segments:
        for item in [*segment.frames, *segment.ocr]:
            owner.setdefault(item.frame, segment.id)
    hits = []
    for entity, file, bbox, score in matches:
        segment_id = owner.get(file)
        t = frame_times.get(file)
        if segment_id is None and t is not None:
            segment_id = next((s.id for s in timeline.segments if s.start <= t <= s.end), None)
        hits.append(
            EntityHit(
                entity=entity,
                via="ref_image",
                segment_id=segment_id,
                frame=file,
                bbox=bbox,
                score=score,
            )
        )
    return hits
