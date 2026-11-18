import json
import os
import shutil
from pathlib import Path

import cv2
import pytest

from h4wk.media import ocr

SAMPLE = Path(__file__).parents[1] / "fixtures" / "ocr" / "vietnamese.png"


@pytest.fixture
def capture(tmp_path):
    raw = tmp_path / "capture"
    derived = tmp_path / "derived"
    (derived / "frames").mkdir(parents=True)
    raw.mkdir()
    frame = derived / "frames/000007.jpg"
    assert cv2.imwrite(str(frame), cv2.imread(str(SAMPLE)))
    shutil.copyfile(SAMPLE, raw / "thumb.png")
    (derived / "frames/index.json").write_text(
        json.dumps(
            {
                "proxy_size": 100,
                "proxy_mtime_ns": 1,
                "settings": {},
                "frames": [{"file": "frames/000007.jpg", "scene": 1, "t": 1.5, "hash": "0" * 16}],
            }
        )
    )
    (raw / "normalized.json").write_text(
        json.dumps(
            {
                "schema": "h4wk.normalized/1",
                "thumbnails": [
                    {"name": "local", "file": "thumb.png"},
                    {"name": "remote", "url": "https://example.org/image"},
                ],
            }
        )
    )
    return raw, derived


def test_process_keyframes_and_local_thumbnails(capture, monkeypatch):
    raw, derived = capture

    def recognize(paths):
        assert paths == [derived / "frames/000007.jpg", raw / "thumb.png"]
        return [[{"text": "LỪA ĐẢO", "bbox": [4, 5, 20, 10], "score": 0.9}], []]

    monkeypatch.setattr(ocr, "_recognize", recognize)
    lines = ocr.process_ocr(raw, derived)
    assert [(line.frame, line.t, line.text) for line in lines] == [
        ("frames/000007.jpg", 1.5, "LỪA ĐẢO")
    ]
    path = derived / "ocr.json"
    assert json.loads(path.read_text())["lines"] == [line.model_dump(mode="json") for line in lines]
    stamp = path.stat().st_mtime_ns
    monkeypatch.setattr(ocr, "_recognize", lambda paths: pytest.fail("cache miss"))
    assert ocr.process_ocr(raw, derived) == lines and path.stat().st_mtime_ns == stamp


def test_retry_keeps_previous_output(capture, monkeypatch):
    raw, derived = capture
    monkeypatch.setattr(ocr, "_recognize", lambda paths: [[] for p in paths])
    assert ocr.process_ocr(raw, derived) == []
    previous = (derived / "ocr.json").read_bytes()
    (raw / "thumb.png").write_bytes(SAMPLE.read_bytes() + b"metadata")

    def fail(paths):
        raise RuntimeError("CPU failure")

    monkeypatch.setattr(ocr, "_recognize", fail)
    with pytest.raises(RuntimeError, match="CPU failure"):
        ocr.process_ocr(raw, derived)
    assert (derived / "ocr.json").read_bytes() == previous


def test_thumbnails_without_video(capture, monkeypatch):
    raw, derived = capture
    (derived / "frames/index.json").unlink()
    monkeypatch.setattr(
        ocr,
        "_recognize",
        lambda paths: [[{"text": "ảnh", "bbox": [0, 0, 4, 4], "score": 0.8}] for path in paths],
    )
    (line,) = ocr.process_ocr(raw, derived)
    assert line.frame == "thumb.png" and line.t is None


@pytest.mark.skipif(os.getenv("H4WK_TEST_OCR") != "1", reason="Chạy model CPU với H4WK_TEST_OCR=1")
def test_real_vietnamese_ocr(capture):
    lines = ocr.process_ocr(*capture)
    assert [(line.frame, line.t) for line in lines] == [
        ("frames/000007.jpg", 1.5),
        ("thumb.png", None),
    ]
    for line in lines:
        assert line.text == "LỪA ĐẢO"
        x, y, w, h = line.bbox
        assert 40 <= x <= 85 and 10 <= y <= 55
        assert 350 <= x + w <= 395 and 90 <= y + h <= 130
        assert 0 < line.score <= 1


def test_full_video_requires_index(capture):
    raw, derived = capture
    (derived / "frames/index.json").unlink()
    normalized = raw / "normalized.json"
    data = json.loads(normalized.read_bytes())
    data["media"] = [{"kind": "video", "file": "video.mp4"}]
    normalized.write_text(json.dumps(data))
    with pytest.raises(FileNotFoundError, match="index.json"):
        ocr.process_ocr(raw, derived)
