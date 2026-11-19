import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from pydantic import BaseModel, ValidationError

from h4wk.ai.base import ProviderError, ProviderReply
from h4wk.ai.config import load_ai_config
from h4wk.ai.fake import FakeProvider
from h4wk.ai.gateway import AIGateway, GatewayError


class Answer(BaseModel):
    label: str


CONFIG = """
[providers.first]
type = "gemini"
[providers.first.models.text]
structured = true
[providers.second]
type = "anthropic"
[providers.second.models.image]
vision = true
[tasks]
"analysis.classify" = [{provider="first", model="text"}, {provider="second", model="image"}]
"media.vision" = [{provider="second", model="image"}]
"""
OK = ProviderReply('{"label":"ok"}', input_tokens=10, output_tokens=4, cost_usd=0.001)


@pytest.fixture
def config(tmp_path):
    path = tmp_path / "ai.toml"
    path.write_text(CONFIG, encoding="utf-8")
    return path


def logs(tmp_path):
    return [
        json.loads(line)
        for line in (tmp_path / "ai_calls.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_repair_invalid_json(config, tmp_path):
    first = FakeProvider([ProviderReply("oops"), OK])
    gateway = AIGateway({"first": first}, config_path=config, log_dir=tmp_path)
    messages = [{"role": "user", "content": "classify"}]
    assert gateway.complete_structured("analysis.classify", messages, Answer) == Answer(label="ok")
    request, retry = first.requests
    assert request.model == "text" and request.structured
    assert request.schema == Answer.model_json_schema()
    assert len(messages) == len(request.messages) == 1
    assert retry.messages[-2]["content"] == "oops"
    assert "json_invalid" in retry.messages[-1]["content"]
    attempts = logs(tmp_path)
    assert [row["status"] for row in attempts] == ["invalid_output", "ok"]
    assert (attempts[1]["input_tokens"], attempts[1]["output_tokens"]) == (10, 4)
    assert attempts[1]["cost_usd"] == 0.001 and attempts[1]["latency_ms"] >= 0


@pytest.mark.parametrize(
    "failures",
    [
        [ProviderError("offline")],
        [ProviderReply("{}")] * 3,
    ],
)
def test_fallback(config, tmp_path, failures):
    first, second = FakeProvider(failures), FakeProvider([OK])
    gateway = AIGateway({"first": first, "second": second}, config_path=config, log_dir=tmp_path)
    assert gateway.complete_structured("analysis.classify", [], Answer).label == "ok"
    assert len(first.requests) == len(failures)
    assert second.requests[0].messages == []
    assert [(r["provider"], r["model"]) for r in logs(tmp_path)] == (
        [("first", "text")] * len(failures) + [("second", "image")]
    )


def test_image_and_route_reload(config, tmp_path):
    second = FakeProvider([OK, OK])
    gateway = AIGateway({"second": second}, config_path=config, log_dir=tmp_path)
    assert gateway.describe_image("media.vision", b"pixels", "describe", Answer).label == "ok"
    request = second.requests[0]
    assert request.image == b"pixels" and request.messages[-1]["content"] == "describe"
    assert request.model == "image" and not request.structured
    config.write_text(CONFIG.replace('{provider="first", model="text"}, ', ""), encoding="utf-8")
    assert gateway.complete_structured("analysis.classify", [], Answer).label == "ok"
    assert [r["status"] for r in logs(tmp_path)] == ["ok", "ok"]


def test_invalid_vision_route(config):
    config.write_text(CONFIG.replace("vision = true", "vision = false"), encoding="utf-8")
    with pytest.raises(ValidationError, match="cannot read images"):
        load_ai_config(config)


def test_exhausted_routes(config, tmp_path):
    gateway = AIGateway(
        {"second": FakeProvider([ProviderError("offline")])}, config_path=config, log_dir=tmp_path
    )
    with pytest.raises(GatewayError, match="media.vision"):
        gateway.describe_image("media.vision", b"pixels", "describe", Answer)
    assert [r["status"] for r in logs(tmp_path)] == ["provider_error"]


def test_limit_is_per_provider(config, tmp_path):
    entered, release, waiting, overlap = Event(), Event(), Event(), Event()

    class BlockingProvider:
        def complete(self, request):
            if entered.is_set():
                overlap.set()
            entered.set()
            assert release.wait(5)
            return OK

    gateway = AIGateway(
        {"first": BlockingProvider(), "second": FakeProvider([OK])},
        config_path=config,
        log_dir=tmp_path,
    )

    def classify():
        waiting.set()
        return gateway.complete_structured("analysis.classify", [], Answer)

    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(gateway.complete_structured, "analysis.classify", [], Answer)
        assert entered.wait(2)
        second = pool.submit(classify)
        assert waiting.wait(2)
        try:
            other = pool.submit(gateway.describe_image, "media.vision", b"img", "describe", Answer)
            assert other.result(timeout=2).label == "ok"
            assert not overlap.wait(0.1)
        finally:
            release.set()
        assert first.result() == second.result() == Answer(label="ok")


def test_missing_key_is_reported(config, tmp_path):
    gateway = AIGateway({}, config_path=config, log_dir=tmp_path)
    with pytest.raises(GatewayError, match="no AI provider available.*missing API key"):
        gateway.describe_image("media.vision", b"pixels", "describe", Answer)
