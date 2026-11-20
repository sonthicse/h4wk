"""describe_images: ảnh lỗi bị bỏ, ảnh còn lại vẫn được ghi vào vision.json."""

import json
from pathlib import Path

import pytest

from h4wk.ai.base import ProviderError, ProviderReply, ProviderRequest
from h4wk.ai.config import AI_CONFIG_PATH
from h4wk.ai.gateway import AIGateway
from h4wk.media import vision

OK = ProviderReply('{"description":"Ảnh mẫu","offensive_cues":[]}')


class ByImage:
    """Trả lời theo nội dung ảnh, không theo thứ tự (các ảnh chạy song song)."""

    def __init__(self, bad: set[bytes]):
        self.bad = bad
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderReply:
        self.requests.append(request)
        if request.image in self.bad:
            raise ProviderError("boom")
        return OK


@pytest.fixture
def images(tmp_path: Path) -> list[tuple[str, Path]]:
    rows = []
    for name in ("a", "b", "c"):
        path = tmp_path / f"{name}.jpg"
        path.write_bytes(name.encode())
        rows.append((f"frames/{name}.jpg", path))
    return rows


def _use(monkeypatch, tmp_path, provider, config_path=None):
    gateway = AIGateway(
        {"anthropic": provider},
        config_path=config_path or AI_CONFIG_PATH.with_suffix(".toml.example"),
        log_dir=tmp_path,
    )
    monkeypatch.setattr(vision, "AIGateway", lambda: gateway)


def test_failed_image_is_skipped_then_retried_alone(monkeypatch, tmp_path, images):
    output = tmp_path / "vision.json"
    _use(monkeypatch, tmp_path, ByImage({b"b"}))
    result = vision.describe_images(images, output)
    assert set(result) == {"frames/a.jpg", "frames/c.jpg"}
    assert set(json.loads(output.read_text(encoding="utf-8"))) == set(result)
    retry = ByImage(set())
    _use(monkeypatch, tmp_path, retry)
    result = vision.describe_images(images, output)
    assert set(result) == {f for f, _ in images}
    assert [r.image for r in retry.requests] == [b"b"]


def test_missing_config_returns_nothing_without_error(monkeypatch, tmp_path, images):
    _use(monkeypatch, tmp_path, ByImage(set()), tmp_path / "none.toml")
    assert vision.describe_images(images, tmp_path / "vision.json") == {}
