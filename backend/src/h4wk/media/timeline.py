"""Hợp đồng C3: timeline.json (SPEC 10.5)."""

from typing import Literal, Self

from pydantic import Field, model_validator

from h4wk.core.types import (
    BBox,
    CaptureTs,
    Contract,
    NonNegFloat,
    RelPath,
    Sha256,
    TranscriptKind,
)


class OcrText(Contract):
    text: str
    bbox: BBox


class Visual(Contract):
    """Mô tả của VLM. Không chứa danh tính người trong ảnh."""

    description: str
    offensive_cues: list[str] = []
    provider: str
    model: str


class FrameOcr(OcrText):
    frame: RelPath
    t: NonNegFloat


class FrameVisual(Visual):
    frame: RelPath
    t: NonNegFloat


class ThumbnailAnalysis(Contract):
    file: RelPath
    ocr: list[OcrText] = []
    visual: Visual | None = None


class Segment(Contract):
    id: str = Field(pattern=r"^seg_\d{4,}$")
    start: NonNegFloat
    end: NonNegFloat
    speech: str = ""
    ocr: list[FrameOcr] = []
    visual: list[FrameVisual] = []

    @model_validator(mode="after")
    def _times(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must be >= start")
        for item in [*self.ocr, *self.visual]:
            if not self.start <= item.t <= self.end:
                raise ValueError(f"frame {item.frame} (t={item.t}) is outside segment {self.id}")
        return self


class Timeline(Contract):
    schema_: Literal["h4wk.timeline/1"] = Field(alias="schema")
    video_id: str
    capture: CaptureTs
    source_video_sha256: Sha256 | None = None  # None khi mức thu không có video
    transcript_kind: TranscriptKind | None = None  # None khi không có transcript nào
    thumbnails: list[ThumbnailAnalysis] = []
    segments: list[Segment] = []

    @model_validator(mode="after")
    def _unique_segment_ids(self) -> Self:
        ids = [s.id for s in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate segment id")
        return self
