import json
from unittest.mock import MagicMock, patch

import pytest

from h4wk.ai.base import ProviderError, ProviderRequest
from h4wk.ai.providers import make_provider
from h4wk.ai.providers.anthropic import AnthropicProvider
from h4wk.ai.providers.gemini import GeminiProvider
from h4wk.ai.providers.openai_compat import OpenAICompatProvider
from h4wk.core.config_models import ProviderConfig

PNG = b"\x89PNG\r\n\x1a\n" + bytes(32)
SCHEMA = {"type": "object", "properties": {"label": {"type": "string"}}}


def request(structured):
    messages = [
        {"role": "system", "content": "policy"},
        {"role": "user", "content": "describe"},
        {"role": "assistant", "content": "oops"},
        {"role": "user", "content": "fix it"},
    ]
    return ProviderRequest("model", messages, SCHEMA, structured, PNG)


@pytest.mark.parametrize("structured", [False, True])
def test_openai_compat(structured):
    with patch("h4wk.ai.providers.openai_compat.OpenAI") as sdk:
        create = sdk.return_value.__enter__.return_value.chat.completions.create
        message = MagicMock(content='{"label":"ok"}', refusal=None)
        message.tool_calls = [
            MagicMock(type="function", function=MagicMock(arguments=message.content))
        ]
        message.tool_calls[0].function.name = "result"
        create.return_value.choices = [MagicMock(message=message, finish_reason="stop")]
        create.return_value.usage = MagicMock(prompt_tokens=5, completion_tokens=2)
        reply = OpenAICompatProvider("test", "https://service.example/v1").complete(
            request(structured)
        )
        assert json.loads(reply.text)["label"] == "ok"
        assert (reply.input_tokens, reply.output_tokens) == (5, 2)
        assert sdk.call_args.kwargs["base_url"] == "https://service.example/v1"
        args = create.call_args.kwargs
        assert args["messages"][-3]["content"][1]["image_url"]["url"].startswith("data:image/png;")
        if structured:
            assert args["tools"][0]["function"]["parameters"] == SCHEMA
        else:
            assert args["response_format"] == {"type": "json_object"}
            assert "label" in args["messages"][0]["content"]


@pytest.mark.parametrize("structured", [False, True])
def test_anthropic(structured):
    with patch("h4wk.ai.providers.anthropic.Anthropic") as sdk:
        create = sdk.return_value.__enter__.return_value.messages.create
        create.return_value.content = [MagicMock(type="text", text='{"label":"ok"}')]
        create.return_value.usage = MagicMock(input_tokens=5, output_tokens=2)
        reply = AnthropicProvider("test").complete(request(structured))
        assert json.loads(reply.text)["label"] == "ok"
        args = create.call_args.kwargs
        assert "policy" in args["system"]
        assert args["messages"][0]["content"][1]["source"]["media_type"] == "image/png"
        if structured:
            assert args["output_config"]["format"]["schema"]["additionalProperties"] is False
        else:
            assert "label" in args["system"]


@pytest.mark.parametrize("structured", [False, True])
def test_gemini(structured):
    with patch("h4wk.ai.providers.gemini.genai.Client") as sdk:
        generate = sdk.return_value.__enter__.return_value.models.generate_content
        generate.return_value.text = '{"label":"ok"}'
        generate.return_value.usage_metadata = MagicMock(
            prompt_token_count=5, candidates_token_count=2
        )
        reply = GeminiProvider("test").complete(request(structured))
        assert json.loads(reply.text)["label"] == "ok"
        args = generate.call_args.kwargs
        assert [m.role for m in args["contents"]] == ["user", "model", "user"]
        assert args["contents"][0].parts[1].inline_data.data == PNG
        config = args["config"]
        assert config.response_mime_type == "application/json"
        assert config.response_json_schema == (SCHEMA if structured else None)
        assert "policy" in config.system_instruction
        if not structured:
            assert "label" in config.system_instruction


def test_private_endpoint_uses_its_own_key():
    config = ProviderConfig(type="openai_compat", base_url="https://service.example/v1", models={})
    assert make_provider("internal", config, {"OPENAI_API_KEY": "unrelated"}) is None
    assert isinstance(
        make_provider("internal", config, {"INTERNAL_API_KEY": "test"}), OpenAICompatProvider
    )


def test_unsupported_image_rejected_before_network():
    req = request(True)
    with pytest.raises(ProviderError):
        AnthropicProvider("test").complete(
            ProviderRequest(req.model, req.messages, SCHEMA, True, b"not an image")
        )


@pytest.mark.parametrize("name", ["anthropic", "gemini", "openai"])
def test_gateway_through_real_sdk(name, monkeypatch, tmp_path):
    import httpx2
    from pydantic import BaseModel

    from h4wk.ai.gateway import AIGateway

    class Result(BaseModel):
        label: str

    # Intercept the final HTTP request after the official SDK serialized the payload.
    def send(client, request, **kwargs):
        payload = json.loads(request.content)
        assert "model" in (payload.get("model") or str(request.url))
        if name == "anthropic":
            assert payload["output_config"]["format"]["schema"]["properties"]["label"]
            response = {
                "id": "id",
                "type": "message",
                "role": "assistant",
                "model": "model",
                "content": [{"type": "text", "text": '{"label":"ok"}'}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 3, "output_tokens": 5},
            }
        elif name == "gemini":
            assert payload["generationConfig"]["responseJsonSchema"]["properties"]["label"]
            response = {
                "candidates": [
                    {
                        "content": {"role": "model", "parts": [{"text": '{"label":"ok"}'}]},
                        "finishReason": "STOP",
                    }
                ]
            }
        else:
            assert request.url.host == "private.example"
            assert payload["tools"][0]["function"]["parameters"]["properties"]["label"]
            response = {
                "id": "id",
                "object": "chat.completion",
                "created": 0,
                "model": "model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call",
                                    "type": "function",
                                    "function": {"name": "result", "arguments": '{"label":"ok"}'},
                                }
                            ],
                        },
                    }
                ],
            }
        return httpx2.Response(200, json=response, request=request)

    monkeypatch.setattr(httpx2.Client, "send", send)
    monkeypatch.setenv(name.upper() + "_API_KEY", "test-only")
    config_path = tmp_path / "ai.toml"
    settings = (
        'type = "openai_compat"\nbase_url = "https://private.example/v1"'
        if name == "openai"
        else f'type = "{name}"'
    )
    config_path.write_text(
        f"[providers.{name}]\n{settings}\n[providers.{name}.models.model]\n"
        f'structured = true\n[tasks]\n"analysis.classify" = '
        f'[{{provider="{name}",model="model"}}]\n',
        encoding="utf-8",
    )
    answer = AIGateway(config_path=config_path, log_dir=tmp_path).complete_structured(
        "analysis.classify", [{"role": "user", "content": "Hello"}], Result
    )
    assert answer.label == "ok"


def test_unsupported_anthropic_schema_allows_gateway_fallback():
    req = ProviderRequest(
        "model",
        [{"role": "user", "content": "hello"}],
        {"type": "object", "properties": {"value": {}}},
        True,
        None,
    )
    with pytest.raises(ProviderError, match="schema"):
        AnthropicProvider("test").complete(req)


def _setup_gateway(name, monkeypatch, tmp_path):
    from h4wk.ai.gateway import AIGateway

    monkeypatch.setenv(name.upper() + "_API_KEY", "test-only")
    settings = (
        'type = "openai_compat"\nbase_url = "https://private.example/v1"'
        if name == "openai"
        else f'type = "{name}"'
    )
    config_path = tmp_path / "ai.toml"
    config_path.write_text(
        f"[providers.{name}]\n{settings}\n[providers.{name}.models.model]\n"
        f'structured = true\n[tasks]\n"analysis.classify" = '
        f'[{{provider="{name}",model="model"}}]\n',
        encoding="utf-8",
    )
    return AIGateway(config_path=config_path, log_dir=tmp_path)


@pytest.mark.parametrize("name", ["anthropic", "gemini", "openai"])
def test_request_timeout_is_set(name, monkeypatch, tmp_path):
    import httpx2
    from pydantic import BaseModel

    from h4wk.ai.base import REQUEST_TIMEOUT_S

    class Result(BaseModel):
        label: str

    seen = []

    def send(client, request, **kwargs):
        seen.append(request.extensions["timeout"]["read"])
        raise httpx2.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(httpx2.Client, "send", send)
    gateway = _setup_gateway(name, monkeypatch, tmp_path)
    with pytest.raises(Exception):  # noqa: B017 - chỉ cần lấy timeout từ request
        gateway.complete_structured("analysis.classify", [{"role": "user", "content": "x"}], Result)
    assert seen
    assert all(abs(read - REQUEST_TIMEOUT_S) < 1 for read in seen)


@pytest.mark.parametrize("name", ["anthropic", "gemini", "openai"])
def test_timeout_raises_provider_error(name, monkeypatch):
    import httpx2

    def send(client, request, **kwargs):
        raise httpx2.ReadTimeout("timed out", request=request)

    monkeypatch.setattr(httpx2.Client, "send", send)
    provider = {
        "anthropic": lambda: AnthropicProvider("test"),
        "gemini": lambda: GeminiProvider("test"),
        "openai": lambda: OpenAICompatProvider("test", "https://private.example/v1"),
    }[name]()
    with pytest.raises(ProviderError):
        provider.complete(request(False))
