"""Hợp đồng C4: dấu hiệu (hits.json), nghi vấn (findings.json), quyết định rà soát
(một dòng trong reviews.jsonl). hits.json và findings.json là mảng JSON (SPEC 10.6)."""

from enum import StrEnum
from itertools import pairwise
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
            raise ValueError("via comment needs comment_id")
        if self.via in (Via.FACE, Via.REF_IMAGE) and not self.frame:
            raise ValueError(f"via {self.via} needs frame")
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


class Occurrence(Contract):
    """Một chỗ nghi vấn xuất hiện trong video (một segment của timeline)."""

    segment_id: str
    start: NonNegFloat
    end: NonNegFloat
    frame: RelPath | None = None

    @model_validator(mode="after")
    def _order(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must be >= start")
        return self


class Finding(Contract):
    """Một nghi vấn (một phần tử của findings.json).

    `occurrences` liệt kê mọi chỗ cùng một nội dung xuất hiện (vd băng rôn chạy suốt video
    được OCR ở nhiều đoạn), theo thứ tự thời gian; `segment_id`, `start`, `end` là chỗ đầu tiên.
    Rỗng khi nghi vấn chỉ ở một chỗ."""

    id: FindingId
    run_id: str
    video_id: str
    capture: CaptureTs
    analyzer: Literal["static", "jev"]
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
    occurrences: list[Occurrence] = []

    @model_validator(mode="before")
    @classmethod
    def _legacy_llm(cls, data):
        """Đọc nghi vấn cũ: `analyzer: "llm"` của Jev (provider `typesafe`) thành `"jev"`.
        Nghi vấn của các LLM khác đã bỏ khỏi dự án nên bị từ chối."""
        if not isinstance(data, dict) or data.get("analyzer") != "llm":
            return data
        model = data.get("model")
        if not (isinstance(model, dict) and model.get("provider") == "typesafe"):
            raise ValueError("findings from removed LLM providers are not supported")
        return {**data, "analyzer": "jev"}

    @model_validator(mode="after")
    def _rules(self) -> Self:
        if self.analyzer == "jev" and self.model is None:
            raise ValueError("a jev finding needs model")
        if self.source_kind == SourceKind.VISUAL and not self.frame:
            raise ValueError("a visual finding needs frame")
        if self.source_kind in _TIMED_KINDS and (not self.segment_id or self.start is None):
            raise ValueError(f"a {self.source_kind} finding needs segment_id and start")
        if self.source_kind == SourceKind.COMMENT and not self.comment_id:
            raise ValueError("a comment finding needs comment_id")
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError("end must be >= start")
        if self.occurrences:
            first = self.occurrences[0]
            if (first.segment_id, first.start) != (self.segment_id, self.start):
                raise ValueError("the first occurrence must match segment_id and start")
            if any(a.start > b.start for a, b in pairwise(self.occurrences)):
                raise ValueError("occurrences must be sorted by start")
        return self


NON_VIOLATIONS = {Category.LEGITIMATE_CRITICISM, Category.NEUTRAL}


class VerdictAnswer(Contract):
    violation: Literal["yes", "no", "uncertain"]
    categories: list[Category] = []
    severity: Severity | None = None
    confidence: Confidence
    summary: str = ""
    finding_ids: list[FindingId] = []

    @model_validator(mode="after")
    def _evidence(self) -> Self:
        if NON_VIOLATIONS.intersection(self.categories):
            raise ValueError("Verdict categories must be violations")
        if self.violation == "no" and self.categories:
            raise ValueError("A no verdict must have no categories")
        if self.violation != "no":
            if not self.categories:
                raise ValueError("Verdict needs categories")
            if self.severity is None:
                raise ValueError("Verdict needs severity")
            if not self.finding_ids:
                raise ValueError("Verdict needs finding_ids")
        return self


class VideoVerdict(VerdictAnswer):
    """Kết luận theo video (verdict.json), một lần chạy một kết luận."""

    run_id: str
    video_id: str
    capture: CaptureTs
    at: VnDatetime

    @model_validator(mode="before")
    @classmethod
    def _legacy_model(cls, data):
        """Đọc kết luận cũ do LLM viết: bỏ trường `model`; kết luận nay sinh theo quy tắc."""
        if isinstance(data, dict) and "model" in data:
            data = {k: v for k, v in data.items() if k != "model"}
        return data


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
            raise ValueError("Reject needs a note")
        return self


class VideoReviewDecision(Contract):
    """Một quyết định rà soát cho kết luận của video."""

    video_id: str
    run_id: str
    status: Literal["confirmed", "rejected", "needs_info"]
    by: Actor
    at: VnDatetime
    note: str = ""

    @model_validator(mode="after")
    def _reject_needs_reason(self) -> Self:
        if self.status == "rejected" and not self.note.strip():
            raise ValueError("Reject needs a note")
        return self
