"""Chọn khung đại diện và khung có thay đổi từ proxy của một bản thu."""

import fcntl
import math
import os
import re
from bisect import bisect_right
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
import numpy as np
from pydantic import Field, ValidationError
from scenedetect import ContentDetector, detect

from h4wk.core.config_models import KeyframeSettings
from h4wk.core.types import Contract
from h4wk.media.files import atomic_output


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
        raise ValueError(f"Proxy không có cảnh: {proxy}")
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
                raise OSError(f"Không giải mã được khung tại {t}s")
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
                raise OSError(f"Không ghi được khung {name}")
            frames.append(
                Keyframe(file=f"frames/{name}", t=t, scene=scene, hash=f"{fingerprint:016x}")
            )
            previous_small, previous_hash = small, fingerprint
    finally:
        capture.release()
    if len({frame.scene for frame in frames}) != len(scenes):
        raise OSError("Không lấy được khung đại diện cho mọi cảnh")
    return frames


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
