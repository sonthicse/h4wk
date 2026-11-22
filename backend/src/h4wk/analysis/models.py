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
    VIOLENCE = "violence"
    HATE = "hate"
    FORGERY = "forgery"
    LEGITIMATE_CRITICISM = "legitimate_criticism"
    NEUTRAL = "neutral"


CONTENT_VIOLATIONS = {Category.STATE_SECRET, Category.VIOLENCE, Category.HATE, Category.FORGERY}


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Confidence(StrEnum):
    UNVERIFIED = "unverified"
    LIKELY = "likely"
    HIGHLY_LIKELY = "highly_likely"


class Trigger(Contract):
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
    entity: str


class ModelRef(Contract):
    provider: str
    model: str


FindingId = Annotated[str, StringConstraints(pattern=r"^f_[0-9A-HJKMNP-TV-Z]{26}$")]


_TIMED_KINDS = {SourceKind.SPEECH, SourceKind.OCR, SourceKind.VISUAL}


class Occurrence(Contract):
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
    entity: str | None = None
    category: Category
    severity: Severity
    confidence: Confidence
    reason: str
    occurrences: list[Occurrence] = []

    @model_validator(mode="before")
    @classmethod
    def _legacy_llm(cls, data):
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
        if self.entity is None and self.category not in CONTENT_VIOLATIONS:
            raise ValueError(f"category {self.category} needs entity")
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
    run_id: str
    video_id: str
    capture: CaptureTs
    at: VnDatetime

    @model_validator(mode="before")
    @classmethod
    def _legacy_model(cls, data):
        if isinstance(data, dict) and "model" in data:
            data = {k: v for k, v in data.items() if k != "model"}
        return data


class ReviewDecision(Contract):
    finding_id: FindingId
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


class VideoReviewDecision(Contract):
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
