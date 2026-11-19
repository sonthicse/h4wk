"""Chuẩn bị nội dung chung; mỗi adapter tự mã hoá ảnh theo giao thức riêng."""

import json
from base64 import b64encode
from dataclasses import dataclass

from h4wk.ai.base import Message, ProviderError, ProviderRequest


@dataclass
class Image:
    data: bytes
    mime: str

    def base64(self) -> str:
        return b64encode(self.data).decode("ascii")


def image_part(data: bytes) -> Image:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return Image(data, "image/png")
    if data.startswith(b"\xff\xd8\xff"):
        return Image(data, "image/jpeg")
    if data.startswith((b"GIF87a", b"GIF89a")):
        return Image(data, "image/gif")
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return Image(data, "image/webp")
    raise ProviderError("unsupported image format")


def split_messages(request: ProviderRequest) -> tuple[str, list[tuple[Message, Image | None]]]:
    instructions = [m["content"] for m in request.messages if m["role"] == "system"]
    if not request.structured:
        instructions.append(
            "Chỉ trả về JSON theo schema sau:\n" + json.dumps(request.schema, ensure_ascii=False)
        )
    image = image_part(request.image) if request.image is not None else None
    turns = []
    for message in request.messages:
        if message["role"] != "system":
            attachment = image if message["role"] == "user" else None
            turns.append((message, attachment))
            if attachment:
                image = None
    return "\n\n".join(instructions), turns
