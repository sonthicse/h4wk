"""Quy ước C3: timeline.json (SPEC 10.5)."""

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


class FrameOcr(OcrText):
    frame: RelPath
    t: NonNegFloat


class Frame(Contract):
    """Keyframe thuộc một đoạn; ảnh gửi thẳng cho Jev, không có mô tả."""

    frame: RelPath
    t: NonNegFloat


class ThumbnailAnalysis(Contract):
    file: RelPath
    ocr: list[OcrText] = []


class Segment(Contract):
    id: str = Field(pattern=r"^seg_\d{4,}$")
    start: NonNegFloat
    end: NonNegFloat
    speech: str = ""
    ocr: list[FrameOcr] = []
    frames: list[Frame] = []

    @model_validator(mode="after")
    def _times(self) -> Self:
        if self.end < self.start:
            raise ValueError("end must be >= start")
        for item in [*self.ocr, *self.frames]:
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

    @model_validator(mode="before")
    @classmethod
    def _legacy_visual(cls, data):
        """Đọc timeline cũ: `visual` của đoạn thành `frames`, `visual` của thumbnail bị bỏ."""
        if not isinstance(data, dict):
            return data
        data = dict(data)
        if isinstance(data.get("segments"), list):
            segments = []
            for seg in data["segments"]:
                if isinstance(seg, dict) and "visual" in seg:
                    seg = dict(seg)
                    old = seg.pop("visual")
                    if "frames" not in seg and isinstance(old, list):
                        # Chỉ giữ frame, t; khóa thiếu hoặc sai kiểu để mô hình Frame báo lỗi.
                        seg["frames"] = [
                            {k: v[k] for k in ("frame", "t") if k in v}
                            if isinstance(v, dict)
                            else v
                            for v in old
                        ]
                    elif "frames" not in seg:
                        seg["frames"] = old  # sai kiểu: để Pydantic từ chối
                segments.append(seg)
            data["segments"] = segments
        if isinstance(data.get("thumbnails"), list):
            data["thumbnails"] = [
                {k: v for k, v in thumb.items() if k != "visual"}
                if isinstance(thumb, dict)
                else thumb
                for thumb in data["thumbnails"]
            ]
        return data

    @model_validator(mode="after")
    def _unique_segment_ids(self) -> Self:
        ids = [s.id for s in self.segments]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate segment id")
        return self
