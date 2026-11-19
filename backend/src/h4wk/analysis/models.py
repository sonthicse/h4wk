"""Hợp đồng C4: dấu hiệu (hits.json), nghi vấn (findings.json), quyết định rà soát
(một dòng trong reviews.jsonl). hits.json và findings.json là mảng JSON (SPEC 10.6)."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import StringConstraints, model_validator

from h4wk.core.types import Actor, BBox, CaptureTs, Contract, NonNegFloat, RelPath, VnDatetime


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
    INCITEMENT = "incitement"
    STATE_SECRET = "state_secret"
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


# id của nghi vấn: `f_` + ULID (26 ký tự Crockford base32), duy nhất trong toàn hệ thống.
FindingId = Annotated[str, StringConstraints(pattern=r"^f_[0-9A-HJKMNP-TV-Z]{26}$")]


# Nghi vấn nằm trong video: cần segment_id và start để phát video từ start − 2s (màn 1).
_TIMED_KINDS = {SourceKind.SPEECH, SourceKind.OCR, SourceKind.VISUAL}


class Finding(Contract):
    """Một nghi vấn (một phần tử của findings.json)."""

    id: FindingId
    run_id: str
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
        if self.source_kind in _TIMED_KINDS and (not self.segment_id or self.start is None):
            raise ValueError(f"nghi vấn {self.source_kind} phải có segment_id và start")
        if self.source_kind == SourceKind.COMMENT and not self.comment_id:
            raise ValueError("nghi vấn từ comment phải có comment_id")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end phải >= start")
        return self


class ReviewDecision(Contract):
    """Một quyết định rà soát (một dòng của reviews.jsonl)."""

    finding_id: FindingId
    run_id: str
    status: Literal["confirmed", "rejected", "needs_info"]
    by: Actor
    at: VnDatetime
    note: str = ""

    @model_validator(mode="after")
    def _reject_needs_reason(self) -> Self:
        # reviews.jsonl chỉ ghi thêm, ghi sai thì không sửa được, nên chặn ngay ở hợp đồng.
        if self.status == "rejected" and not self.note.strip():
            raise ValueError("Reject phải có lý do (note)")
        return self
