"""Chạy trực tiếp từng nhà cung cấp có khóa, không chuyển sang nhà cung cấp khác."""

import os
import struct
import zlib
from binascii import crc32

import pytest
from dotenv import dotenv_values
from pydantic import BaseModel

from h4wk.ai.base import ProviderRequest
from h4wk.ai.config import AI_CONFIG_PATH, load_ai_config
from h4wk.ai.providers import make_provider
from h4wk.core.config import REPO_ROOT

pytestmark = pytest.mark.live
path = AI_CONFIG_PATH if AI_CONFIG_PATH.exists() else AI_CONFIG_PATH.with_suffix(".toml.example")
config = load_ai_config(path)
cases = []
for name, provider_config in config.providers.items():
    for model, caps in provider_config.models.items():
        cases.append(pytest.param(name, model, False, id=f"{name}-{model}-text"))
        if caps.vision:
            cases.append(pytest.param(name, model, True, id=f"{name}-{model}-image"))


class Answer(BaseModel):
    color: str


def red_png() -> bytes:
    def chunk(kind, payload):
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", crc32(kind + payload))
        )

    width = 128
    pixels = (b"\x00" + b"\xff\x00\x00" * width) * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, width, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )


@pytest.mark.parametrize("name,model,image", cases)
def test_ai_provider_live(name, model, image):
    settings = config.providers[name]
    provider = make_provider(name, settings, {**dotenv_values(REPO_ROOT / ".env"), **os.environ})
    if provider is None:
        pytest.skip(f"Thiếu API key cho {name}")
    prompt = (
        "Identify the solid color of this image using one lowercase English color word."
        if image
        else "Return the lowercase English color word red."
    )
    request = ProviderRequest(
        model,
        [{"role": "user", "content": prompt}],
        Answer.model_json_schema(),
        settings.models[model].structured,
        red_png() if image else None,
    )
    assert Answer.model_validate_json(provider.complete(request).text).color.lower() == "red"
