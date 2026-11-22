"""Lấy khung ứng viên từ proxy của một bản thu, rồi chọn keyframe theo hình và chữ OCR."""

import fcntl
import json
import math
import os
import re
import unicodedata
from bisect import bisect_right
from difflib import SequenceMatcher
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from pydantic import Field, ValidationError
from scenedetect import ContentDetector, detect

from h4wk.core.types import Contract
from h4wk.media.files import atomic_output


class KeyframeSettings(Contract):
    """Ngưỡng giữ khung. Không nằm trong analysis.toml (quy ước C5 không có mục này)."""

    phash_threshold: int = Field(default=6, ge=0, le=64)  # số bit khác nhau trong pHash 64 bit
    tile_threshold: float = Field(default=2.0, ge=0, le=255)  # lệch trung bình mỗi ô, 0–255


class Keyframe(Contract):
    file: str = Field(pattern=r"^frames/[0-9]{6,}\.jpg$")
    t: float = Field(ge=0)
    scene: int = Field(ge=1)
    hash: str = Field(pattern=r"^[0-9a-f]{16}$")


class FrameIndex(Contract):
    proxy_size: int
    proxy_mtime_ns: int
    settings: KeyframeSettings
    frames: list[Keyframe] = Field(min_length=1)


def _phash(small: np.ndarray) -> int:
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    pixels = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    low = cv2.dct(pixels.astype(np.float32))[:8, :8].flatten()
    bits = low > np.median(low[1:])
    return int.from_bytes(np.packbits(bits).tobytes(), "big")


def _extract(proxy: Path, staging: Path, settings: KeyframeSettings) -> list[Keyframe]:
    scenes = detect(proxy, ContentDetector(min_scene_len=1), start_in_scene=True)
    starts = [start.seconds for start, _ in scenes]
    if not starts:
        raise ValueError(f"proxy has no scenes: {proxy}")
    frames = []
    previous_scene = 0
    previous_small = None
    previous_hash = 0
    previous_slot = -1
    capture = cv2.VideoCapture(str(proxy))
    try:
        while capture.grab():
            t = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
            # PySceneDetect làm tròn timestamp tới microsecond.
            scene = max(1, bisect_right(starts, t + 0.000001))
            slot = math.floor((t - starts[scene - 1] + 0.000001) * 2)
            if scene == previous_scene and slot == previous_slot:
                continue
            new_scene = scene != previous_scene
            previous_scene, previous_slot = scene, slot
            ok, frame = capture.retrieve()
            if not ok:
                raise OSError(f"cannot decode frame at {t}s")
            small = cv2.resize(frame, (256, 144), interpolation=cv2.INTER_AREA)
            fingerprint = _phash(small)
            if (
                not new_scene
                and (fingerprint ^ previous_hash).bit_count() <= settings.phash_threshold
            ):
                # 4 hàng × 4 cột; lấy trung bình trên pixel và ba kênh trong từng ô.
                tiles = cv2.absdiff(small, previous_small).reshape(4, 36, 4, 64, 3)
                if tiles.mean(axis=(1, 3, 4)).max() <= settings.tile_threshold:
                    continue
            number = int(capture.get(cv2.CAP_PROP_POS_FRAMES))
            name = f"{number:06d}.jpg"
            if not cv2.imwrite(str(staging / name), frame):
                raise OSError(f"cannot write frame {name}")
            frames.append(
                Keyframe(file=f"frames/{name}", t=t, scene=scene, hash=f"{fingerprint:016x}")
            )
            previous_small, previous_hash = small, fingerprint
    finally:
        capture.release()
    if len({frame.scene for frame in frames}) != len(scenes):
        raise OSError("cannot get a representative frame for every scene")
    return frames


SELECTED_FILE = "selected.json"
TEXT_MIN_SCORE = 0.8  # dòng OCR dưới ngưỡng này hay là nhiễu, không tính là chữ mới
TEXT_MIN_CHARS = 4
TEXT_SAME_RATIO = 0.8  # hai dòng giống nhau từ mức này coi là một (OCR đọc lệch vài ký tự)


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.casefold()).replace("đ", "d")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def select_keyframes(
    candidates: list[Keyframe],
    texts: dict[str, list[tuple[str, float]]],
    vectors: np.ndarray | None,
    similarity: float = 0.85,
) -> list[Keyframe]:
    """Chọn keyframe từ các khung ứng viên (đã OCR).

    Giữ khung khi (1) có dòng chữ chưa thấy ở keyframe giữ ngay trước, hoặc (2) khác về hình
    với mọi keyframe đã giữ: cosine của embedding ảnh (L2 đã chuẩn hoá) với từng khung đã giữ
    đều dưới `similarity`. So với mọi khung đã giữ, không chỉ khung trước, để cảnh quay lại
    (phỏng vấn cắt qua lại) không bị giữ lặp. `texts` là các cặp (chữ, score) theo file khung.
    `vectors` None (không có model ảnh) thì chỉ bỏ được khung trùng chữ và trùng hash."""
    kept: list[Keyframe] = []
    kept_vectors: list[np.ndarray] = []
    previous_text: list[str] = []
    for i, frame in enumerate(candidates):
        lines = [
            folded
            for text, score in texts.get(frame.file, [])
            if score >= TEXT_MIN_SCORE
            and len((folded := _fold(text)).replace(" ", "")) >= TEXT_MIN_CHARS
        ]
        new_text = any(
            all(_ratio(line, seen) < TEXT_SAME_RATIO for seen in previous_text) for line in lines
        )
        if vectors is None:
            different = not kept or frame.hash != kept[-1].hash
        else:
            different = all(float(vectors[i] @ v) < similarity for v in kept_vectors)
        if new_text or different:
            kept.append(frame)
            previous_text = lines
            if vectors is not None:
                kept_vectors.append(vectors[i])
    return kept


def write_selected(derived_dir: Path, frames: list[Keyframe]) -> None:
    """Ghi keyframe đã chọn vào frames/selected.json (index.json vẫn là các khung ứng viên)."""
    content = json.dumps([f.model_dump() for f in frames], indent=2) + "\n"
    with atomic_output(derived_dir / "frames" / SELECTED_FILE) as path:
        path.write_text(content, encoding="utf-8")


def extract_keyframes(
    derived_dir: Path, settings: KeyframeSettings | None = None
) -> list[Keyframe]:
    """Đọc proxy_480p.mp4, trả các khung theo thứ tự thời gian. Đường dẫn tính từ derived_dir."""
    settings = settings or KeyframeSettings()
    proxy = derived_dir / "proxy_480p.mp4"
    source = proxy.stat()
    folder = derived_dir / "frames"
    folder.mkdir(exist_ok=True)
    index_path = folder / "index.json"
    lock = os.open(folder, os.O_RDONLY)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if index_path.exists():
            try:
                index = FrameIndex.model_validate_json(index_path.read_bytes())
            except ValidationError:
                pass
            else:
                if (
                    index.settings == settings
                    and index.proxy_size == source.st_size
                    and index.proxy_mtime_ns == source.st_mtime_ns
                    and all(cv2.imread(str(derived_dir / f.file)) is not None for f in index.frames)
                ):
                    return index.frames
        with TemporaryDirectory(dir=folder) as temp:
            staging = Path(temp)
            frames = _extract(proxy, staging, settings)
            for jpeg in staging.iterdir():
                jpeg.replace(folder / jpeg.name)
            index = FrameIndex(
                proxy_size=source.st_size,
                proxy_mtime_ns=source.st_mtime_ns,
                settings=settings,
                frames=frames,
            )
            with atomic_output(index_path) as path:
                path.write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
        kept = {f.file for f in frames}
        for jpeg in folder.glob("*.jpg"):
            if re.fullmatch(r"[0-9]{6,}\.jpg", jpeg.name) and f"frames/{jpeg.name}" not in kept:
                jpeg.unlink()
        return frames
    finally:
        os.close(lock)
