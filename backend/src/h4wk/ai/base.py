"""Giao diện adapter cho một lần gọi model."""

from dataclasses import dataclass
from typing import Any, Protocol, TypedDict


class Message(TypedDict):
    role: str
    content: str


@dataclass(frozen=True)
class ProviderRequest:
    model: str
    messages: list[Message]
    schema: dict[str, Any]
    structured: bool
    image: bytes | None


@dataclass(frozen=True)
class ProviderReply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class ProviderError(RuntimeError):
    """Adapter chuyển lỗi dịch vụ hoặc kết nối sang kiểu này để gateway chuyển nguồn."""


class Provider(Protocol):
    def complete(self, request: ProviderRequest) -> ProviderReply: ...
