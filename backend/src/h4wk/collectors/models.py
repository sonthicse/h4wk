"""Hợp đồng C2: mô hình dữ liệu chung, lưu thành normalized.json (SPEC 10.3)."""

from typing import Literal, Self

from pydantic import Field, model_validator

from h4wk.core.types import (
    Cap,
    CollectLevel,
    Contract,
    NonNegFloat,
    NonNegInt,
    RelPath,
    TranscriptKind,
    VnDatetime,
)

__all__ = [
    "Cap",
    "Channel",
    "CollectLevel",
    "Comment",
    "MediaFile",
    "Normalized",
    "Thumbnail",
    "Transcript",
    "TranscriptKind",
    "TranscriptSegment",
    "Video",
]


class Video(Contract):
    id: str
    channel_id: str
    title: str
    description: str = ""
    tags: list[str] = []
    category: str | None = None
    duration_s: NonNegFloat | None = None
    published_at: VnDatetime | None = None
    view_count: NonNegInt | None = None
    like_count: NonNegInt | None = None
    comment_count: NonNegInt | None = None
    availability: str | None = None  # public, unlisted, private… theo nguồn trả về
    is_live: bool = False


class Channel(Contract):
    id: str
    handle: str | None = None
    title: str
    description: str = ""
    country: str | None = None
    created_at: VnDatetime | None = None
    subscriber_count: NonNegInt | None = None
    view_count: NonNegInt | None = None
    video_count: NonNegInt | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    links: list[str] = []


class TranscriptSegment(Contract):
    start: NonNegFloat
    end: NonNegFloat
    text: str

    @model_validator(mode="after")
    def _end_after_start(self) -> Self:
        if self.end < self.start:
            raise ValueError("end phải >= start")
        return self


class Transcript(Contract):
    kind: TranscriptKind
    lang: str
    segments: list[TranscriptSegment]


class Comment(Contract):
    id: str
    parent_id: str | None = None  # None là comment gốc; có giá trị là reply
    author_channel_id: str | None = None
    text: str
    published_at: VnDatetime | None = None
    like_count: NonNegInt | None = None

    @model_validator(mode="after")
    def _not_own_parent(self) -> Self:
        if self.parent_id == self.id:
            raise ValueError("comment không thể là reply của chính nó")
        return self


class Thumbnail(Contract):
    name: str  # maxres, 0, 1, 2, 3…
    url: str | None = None
    file: RelPath | None = None  # đường dẫn trong bản thu, nếu đã tải
    width: NonNegInt | None = None
    height: NonNegInt | None = None


class MediaFile(Contract):
    kind: Literal["video", "audio"]  # video có thể kèm cả audio
    file: RelPath
    height: NonNegInt | None = None
    vcodec: str | None = None
    acodec: str | None = None
    duration_s: NonNegFloat | None = None


class Normalized(Contract):
    schema_: Literal["h4wk.normalized/1"] = Field(alias="schema")
    video: Video | None = None
    channel: Channel | None = None
    # ID video lấy được từ CHANNEL_VIDEOS hoặc PLAYLIST_VIDEOS.
    video_ids: list[str] = []
    transcripts: list[Transcript] = []
    comments: list[Comment] = []
    thumbnails: list[Thumbnail] = []
    media: list[MediaFile] = []
    # Loại dữ liệu → nguồn đã cung cấp nó.
    provenance: dict[Cap, str] = {}
