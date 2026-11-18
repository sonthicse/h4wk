"""Adapter trả các phản hồi định sẵn cho kiểm thử."""

from collections.abc import Iterable

from h4wk.ai.base import ProviderError, ProviderReply, ProviderRequest


class FakeProvider:
    def __init__(self, replies: Iterable[ProviderReply | ProviderError]):
        self.replies = iter(replies)
        self.requests: list[ProviderRequest] = []

    def complete(self, request: ProviderRequest) -> ProviderReply:
        self.requests.append(request)
        reply = next(self.replies)
        if isinstance(reply, ProviderError):
            raise reply
        return reply
