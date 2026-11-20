"""Giao diện adapter cho một lần gọi model."""

from dataclasses import dataclass
from typing import Any, Protocol, TypedDict

# Giới hạn thời gian mỗi lần gọi provider; tránh treo hàng đợi gpu (worker `-w 1`).
REQUEST_TIMEOUT_S = 120


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
