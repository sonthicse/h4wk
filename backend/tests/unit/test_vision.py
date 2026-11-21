"""describe_images: ảnh lỗi bị bỏ, ảnh còn lại vẫn được ghi vào vision.json."""

import json
from concurrent.futures import ThreadPoolExecutor
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


def test_changed_prompt_invalidates_cache(monkeypatch, tmp_path, images):
    prompt = tmp_path / "vision.md"
    prompt.write_text("Mô tả hình ảnh.", encoding="utf-8")
    monkeypatch.setattr(vision, "PROMPT_PATH", prompt)
    output = tmp_path / "vision.json"
    provider = ByImage(set())
    _use(monkeypatch, tmp_path, provider)
    vision.describe_images(images[:1], output)
    vision.describe_images(images[:1], output)
    assert len(provider.requests) == 1

    prompt.write_text("Mô tả chi tiết hình ảnh.", encoding="utf-8")
    vision.describe_images(images[:1], output)
    assert len(provider.requests) == 2


def test_cache_tracks_only_vision_route(monkeypatch, tmp_path, images):
    original = AI_CONFIG_PATH.with_suffix(".toml.example").read_text(encoding="utf-8")
    config = tmp_path / "ai.toml"
    output = tmp_path / "vision.json"
    provider = ByImage(set())
    _use(monkeypatch, tmp_path, provider, config)

    def change_model(text, task, model):
        lines = text.splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith(f'"{task}" ='))
        lines[index] = f'"{task}" = [{{ provider = "anthropic", model = "{model}" }}]'
        config.write_text("\n".join(lines), encoding="utf-8")

    config.write_text(original, encoding="utf-8")
    vision.describe_images(images[:1], output)
    change_model(original, "analysis.video_verdict", "claude-sonnet-5-5")
    vision.describe_images(images[:1], output)
    assert len(provider.requests) == 1
    change_model(original, "media.vision", "claude-haiku-5-5")
    result = vision.describe_images(images[:1], output)
    assert len(provider.requests) == 2
    assert result[images[0][0]].model == "claude-haiku-5-5"


def test_cache_persisted_before_interruption(monkeypatch, tmp_path, images):
    output = tmp_path / "vision.json"
    fourth = tmp_path / "d.jpg"
    fourth.write_bytes(b"d")
    images.append(("frames/d.jpg", fourth))
    expected = {file for file, _ in images[:2]}

    class Interrupt(ByImage):
        def complete(self, request):
            if request.image in {b"c", b"d"}:
                assert set(json.loads(output.read_text(encoding="utf-8"))) == expected
                raise KeyboardInterrupt
            return super().complete(request)

    # Một luồng để ngắt đúng sau hai ảnh, không phụ thuộc lịch chạy.
    monkeypatch.setattr(vision, "ThreadPoolExecutor", lambda **_: ThreadPoolExecutor(1))
    _use(monkeypatch, tmp_path, Interrupt(set()))
    with pytest.raises(KeyboardInterrupt):
        vision.describe_images(images, output)
    retry = ByImage(set())
    _use(monkeypatch, tmp_path, retry)
    assert set(vision.describe_images(images, output)) == {file for file, _ in images}
    assert [request.image for request in retry.requests] == [b"c", b"d"]


def test_missing_config_returns_nothing_without_error(monkeypatch, tmp_path, images):
    _use(monkeypatch, tmp_path, ByImage(set()), tmp_path / "none.toml")
    assert vision.describe_images(images, tmp_path / "vision.json") == {}


def test_missing_config_keeps_existing_cache(monkeypatch, tmp_path, images):
    output = tmp_path / "vision.json"
    _use(monkeypatch, tmp_path, ByImage(set()))
    vision.describe_images(images[:2], output)
    before = output.read_bytes()
    _use(monkeypatch, tmp_path, ByImage(set()), tmp_path / "none.toml")
    assert vision.describe_images(images, output) == {}
    assert output.read_bytes() == before
    assert len(json.loads(before)) == 2


def test_failed_image_keeps_its_old_cache_row(monkeypatch, tmp_path, images):
    output = tmp_path / "vision.json"
    _use(monkeypatch, tmp_path, ByImage(set()))
    vision.describe_images(images, output)
    images[1][1].write_bytes(b"changed")  # cache của ảnh b lỗi thời, lần này VLM lỗi
    _use(monkeypatch, tmp_path, ByImage({b"changed"}))
    result = vision.describe_images(images, output)
    assert set(result) == {"frames/a.jpg", "frames/c.jpg"}
    assert set(json.loads(output.read_text(encoding="utf-8"))) == {f for f, _ in images}


def test_enrich_skips_frames_without_visual_or_ocr(monkeypatch, tmp_path):
    from h4wk.media import enrich as enrich_module
    from h4wk.media.keyframes import Keyframe
    from h4wk.media.timeline import Timeline

    monkeypatch.setattr(enrich_module, "describe_images", lambda images, output: {})
    timeline = Timeline(schema="h4wk.timeline/1", video_id="v", capture="20261118T160000")
    frame = Keyframe(file="frames/000001.jpg", t=3.0, scene=1, hash="0" * 16)
    failed = enrich_module.enrich(timeline, tmp_path, tmp_path, [frame], [], [])
    assert failed == ["frames/000001.jpg"]
    assert timeline.segments == []
