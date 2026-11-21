"""Nguồn thu giả và fixture dùng chung cho test tích hợp luồng collect → media → analyze.

Không đặt trong conftest.py vì test_auth.py import `conftest` của thư mục tests/."""

import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from h4wk.collectors import registry
from h4wk.collectors.base import Blocked, FetchResult
from h4wk.collectors.models import Cap, Normalized
from h4wk.jobs import pipeline, queue
from h4wk.media import ocr, stt

SAMPLE = (
    Path(__file__).resolve().parents[1] / "fixtures/captures/h4wkDemo001/captures/20261118T160000"
)
VIDEO = "https://www.youtube.com/watch?v=h4wkDemo001"


class SampleCollector:
    """Nguồn giả trả về dữ liệu của bản thu mẫu T44."""

    name = "fake"
    capabilities = set(Cap)
    version = "fake-1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.n = Normalized.model_validate_json(
            (SAMPLE / "normalized.json").read_text(encoding="utf-8")
        )

    def fetch(self, cap: Cap, target, workdir: Path) -> FetchResult:  # noqa: ANN001
        if self.fail:
            raise Blocked("bị chặn")
        data = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            data["video"] = self.n.video
        elif cap == Cap.TRANSCRIPTS:
            data["transcripts"] = self.n.transcripts
        elif cap == Cap.COMMENTS:
            data["comments"] = self.n.comments
        elif cap == Cap.THUMBNAILS:
            shutil.copy(SAMPLE / "sources/ytdlp/maxres.jpg", workdir / "maxres.jpg")
            data["thumbnails"] = [
                {
                    "name": "maxres",
                    "file": f"sources/{workdir.name}/maxres.jpg",
                    "url": "https://example.com/t.jpg",
                }
            ]
        elif cap == Cap.MEDIA:
            shutil.copy(SAMPLE / "sources/ytdlp/h4wkDemo001.mp4", workdir / "v.mp4")
            data["media"] = [{"kind": "video", "file": f"sources/{workdir.name}/v.mp4"}]
        return FetchResult(normalized=Normalized.model_validate(data))

    def health_check(self):  # noqa: ANN201
        raise NotImplementedError


@pytest.fixture
def fake_source(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch, data_dir: Path
) -> dict:
    holder = {"fail": False}
    monkeypatch.setattr(registry, "COLLECTORS", {"fake": lambda: SampleCollector(holder["fail"])})
    if request.node.get_closest_marker("gpu"):
        model = os.getenv("H4WK_STT_MODEL")
        if not model:
            pytest.skip("Cần H4WK_STT_MODEL để kiểm tra worker GPU")
    else:
        model = "test"
        monkeypatch.setattr(
            stt, "_load_model", lambda _: SimpleNamespace(transcribe=lambda *a, **kw: ([], None))
        )
    monkeypatch.setattr(pipeline, "_stt_worker", stt.SttWorker(model))
    monkeypatch.setattr(
        ocr,
        "_recognize",
        lambda paths: [[{"text": "Chữ", "bbox": [0, 0, 1, 1], "score": 1}] for _ in paths],
    )
    # Mọi khung giống hệt nhau về hình: bước chọn keyframe chỉ giữ khung đầu (chữ "Chữ" quá ngắn).
    monkeypatch.setattr(
        pipeline,
        "_ref_embedder",
        SimpleNamespace(embed=lambda images: np.ones((len(images), 4)) / 2),
    )
    return holder


@pytest.fixture(autouse=True)
def _immediate(data_dir: Path) -> Iterator[None]:
    queue.huey.immediate = True
    queue.huey_gpu.immediate = True
    yield
    for root, dirs, _ in os.walk(data_dir):
        for d in dirs:
            os.chmod(Path(root) / d, 0o755)
