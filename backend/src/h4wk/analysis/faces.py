"""Khớp khuôn mặt cục bộ; không lưu đặc trưng ảnh đầu vào."""

import hashlib
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from h4wk.analysis import refimages
from h4wk.core.config import data_dir

MODELS = (
    (
        "face_detection_yunet",
        "face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    (
        "face_recognition_sface",
        "face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
)


def _model(folder: Path, repo: str, name: str, digest: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        return path
    with TemporaryDirectory(dir=folder) as temp:
        with urlopen(
            f"https://huggingface.co/opencv/{repo}/resolve/main/{name}", timeout=60
        ) as response:
            content = response.read(40_000_001)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ValueError(f"Invalid model checksum: {name}")
        candidate = Path(temp) / name
        candidate.write_bytes(content)
        candidate.replace(path)
    return path


@lru_cache(maxsize=1)
def _models(folder: Path):
    import cv2

    detector, recognizer = (_model(folder, *model) for model in MODELS)
    return (
        cv2.FaceDetectorYN.create(str(detector), "", (320, 320)),
        cv2.FaceRecognizerSF.create(str(recognizer), ""),
    )


def _features(path, detector, recognizer):
    import cv2

    image = cv2.imread(str(path))
    if image is None:
        return
    height, width = image.shape[:2]
    detector.setInputSize((width, height))
    _, rows = detector.detect(image)
    if rows is not None:
        for row in rows:
            x, y, w, h = map(round, row[:4])
            left, top = max(0, x), max(0, y)
            right, bottom = min(width, x + w), min(height, y + h)
            if left < right and top < bottom:
                yield (
                    (left, top, right - left, bottom - top),
                    recognizer.feature(recognizer.alignCrop(image, row)),
                )


def match_faces(images, refs, threshold=0.363):
    if not images or not refs:
        return []
    detector, recognizer = _models(data_dir() / "models")
    reference = {
        entity: [v for path in paths for _, v in _features(path, detector, recognizer)]
        for entity, paths in refs.items()
    }
    matches = []
    for file, path in images:
        for bbox, feature in _features(path, detector, recognizer):
            for entity, vectors in reference.items():
                score = max((recognizer.match(feature, v, 0) for v in vectors), default=-1.0)
                if score >= threshold:
                    matches.append((entity, file, bbox, min(1.0, float(score))))
    return matches


def to_hits(matches, timeline, frame_times):
    return [
        hit.model_copy(update={"via": "face"})
        for hit in refimages.to_hits(matches, timeline, frame_times)
    ]
