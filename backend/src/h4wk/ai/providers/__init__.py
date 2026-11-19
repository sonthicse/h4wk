"""Liên kết tên nhà cung cấp trong C5 với adapter và khóa riêng."""

from collections.abc import Mapping

from h4wk.ai.base import Provider
from h4wk.ai.providers.anthropic import AnthropicProvider
from h4wk.ai.providers.gemini import GeminiProvider
from h4wk.ai.providers.openai_compat import OpenAICompatProvider
from h4wk.core.config_models import ProviderConfig


def key_name(provider: str) -> str:
    """Tên biến chứa khóa của một nhà cung cấp, vd anthropic → ANTHROPIC_API_KEY."""
    base = {"qwen": "DASHSCOPE", "glm": "ZAI", "kimi": "MOONSHOT"}.get(provider)
    return (base or provider.upper().replace("-", "_")) + "_API_KEY"


def make_provider(
    name: str, config: ProviderConfig, keys: Mapping[str, str | None]
) -> Provider | None:
    key = keys.get(key_name(name))
    if name == "gemini" and not key:
        key = keys.get("GOOGLE_API_KEY")
    if not key:
        return None
    if config.type == "anthropic":
        return AnthropicProvider(key)
    if config.type == "gemini":
        return GeminiProvider(key)
    return OpenAICompatProvider(key, str(config.base_url))
