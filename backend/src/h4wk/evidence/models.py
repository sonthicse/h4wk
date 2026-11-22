from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from h4wk.core.types import (
    Actor,
    Cap,
    CaptureTs,
    CollectLevel,
    Contract,
    NonNegInt,
    RelPath,
    Sha256,
    VnDatetime,
)


class SourceStatus(StrEnum):
    OK = "ok"
    FAILED = "failed"
    BLOCKED = "blocked"
    QUOTA_EXCEEDED = "quota_exceeded"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"
    DISABLED = "disabled"
    SUSPENDED = "suspended"
    NO_SOURCE = "no_source"


class Trigger(Contract):
    type: Literal["manual", "watchlist"]
    watch_item: str | None = None
    event: str | None = None

    @model_validator(mode="after")
    def _watchlist_needs_item(self) -> Self:
        if self.type == "watchlist" and not self.watch_item:
            raise ValueError("a watchlist trigger needs watch_item")
        return self


class Cost(Contract):
    quota_units: NonNegInt | None = None
    credits: NonNegInt | None = None


class SourceCall(Contract):
    provider: str | None
    what: Cap
    status: SourceStatus
    started_at: VnDatetime | None = None
    duration_ms: NonNegInt | None = None
    cost: Cost | None = None
    error: str | None = None
    version: str | None = None

    @model_validator(mode="after")
    def _provider_null_iff_no_source(self) -> Self:
        if (self.provider is None) != (self.status == SourceStatus.NO_SOURCE):
            raise ValueError("provider is null if and only if status is no_source")
        return self


class FileEntry(Contract):
    sha256: Sha256
    bytes: NonNegInt


class Manifest(Contract):
    schema_: Literal["h4wk.manifest/1"] = Field(alias="schema")
    source_url: str
    collected_at: VnDatetime
    collector: Actor
    trigger: Trigger
    level: CollectLevel
    tool_version: str
    sources: list[SourceCall]
    files: dict[RelPath, FileEntry]
    previous_capture: CaptureTs | None = None
