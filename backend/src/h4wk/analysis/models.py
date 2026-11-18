"""Hợp đồng C4: dấu hiệu (hits.json), nghi vấn (findings.json), quyết định rà soát
(một dòng trong reviews.jsonl). hits.json và findings.json là mảng JSON (SPEC 10.6)."""

import hashlib
import json
from enum import StrEnum
from typing import Literal, Self

from pydantic import Field, model_validator

from h4wk.core.types import Actor, BBox, CaptureTs, Contract, NonNegFloat, RelPath, UtcDatetime


class Via(StrEnum):
    SPEECH = "speech"
    OCR = "ocr"
    TITLE = "title"
    DESCRIPTION = "description"
    COMMENT = "comment"
    THUMBNAIL = "thumbnail"
    FACE = "face"
    REF_IMAGE = "ref_image"


class SourceKind(StrEnum):
    SPEECH = "speech"
    OCR = "ocr"
    VISUAL = "visual"
    TITLE = "title"
    DESCRIPTION = "description"
    THUMBNAIL = "thumbnail"
    COMMENT = "comment"


class Category(StrEnum):
    INSULT = "insult"
    UNSUPPORTED_ACCUSATION = "unsupported_accusation"
    FABRICATION = "fabrication"
    LEGITIMATE_CRITICISM = "legitimate_criticism"
    NEUTRAL = "neutral"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(StrEnum):
    """Mức tin cậy viết bằng chữ, không dùng phần trăm."""

    UNVERIFIED = "unverified"
    LIKELY = "likely"
    HIGHLY_LIKELY = "highly_likely"


class Trigger(Contract):
    """Dấu hiệu đã kéo một đoạn vào phân tích."""

    via: Via
    segment_id: str | None = None
    comment_id: str | None = None
    frame: RelPath | None = None
    bbox: BBox | None = None
    score: float | None = None

    @model_validator(mode="after")
    def _location(self) -> Self:
        if self.via == Via.COMMENT and not self.comment_id:
            raise ValueError("via comment phải có comment_id")
        if self.via in (Via.FACE, Via.REF_IMAGE) and not self.frame:
            raise ValueError(f"via {self.via} phải có frame")
        return self


class EntityHit(Trigger):
    """Một dấu hiệu đối tượng (một phần tử của hits.json)."""

    entity: str


class ModelRef(Contract):
    provider: str
    model: str


def finding_key(
    video_id: str, source_kind: str, location_id: str | None, entity: str, analyzer: str
) -> str:
    """Mã của nghi vấn, giữ nguyên giữa các lần chạy để giữ quyết định rà soát cũ.

    location_id là segment_id, hoặc comment_id với nghi vấn từ comment. Mã là SHA-256 (hex)
    của mảng JSON 5 phần tử theo đúng thứ tự trên, viết gọn, không thoát ký tự Unicode.
    """
    raw = json.dumps(
        [video_id, source_kind, location_id, entity, analyzer],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class Finding(Contract):
    """Một nghi vấn (một phần tử của findings.json)."""

    id: str = Field(pattern=r"^f_\S+$")
    key: str
    run_id: str
    case_id: str
    video_id: str
    capture: CaptureTs
    analyzer: Literal["static", "llm"]
    analyzer_version: str
    model: ModelRef | None = None
    source_kind: SourceKind
    triggers: list[Trigger] = []
    segment_id: str | None = None
    comment_id: str | None = None
    start: NonNegFloat | None = None
    end: NonNegFloat | None = None
    quote: str = ""
    frame: RelPath | None = None
    bbox: BBox | None = None
    entity: str
    category: Category
    severity: Severity
    confidence: Confidence
    reason: str

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.analyzer == "llm" and self.model is None:
            raise ValueError("nghi vấn llm phải có model")
        if self.source_kind == SourceKind.VISUAL and not self.frame:
            raise ValueError("nghi vấn visual phải trích khung hình (frame)")
        if self.source_kind == SourceKind.COMMENT and not self.comment_id:
            raise ValueError("nghi vấn từ comment phải có comment_id")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end phải >= start")
        location = self.comment_id if self.source_kind == SourceKind.COMMENT else self.segment_id
        expected = finding_key(
            self.video_id, self.source_kind, location, self.entity, self.analyzer
        )
        if self.key != expected:
            raise ValueError("key không khớp với (video_id, source_kind, vị trí, entity, analyzer)")
        return self


class ReviewDecision(Contract):
    """Một quyết định rà soát (một dòng của reviews.jsonl)."""

    finding_key: str
    finding_id: str
    run_id: str
    status: Literal["confirmed", "rejected", "needs_info"]
    by: Actor
    at: UtcDatetime
    note: str = ""
