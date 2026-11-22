"""Kiểu dùng chung cho các mô hình dữ liệu.

Các enum `Cap` và `CollectLevel` thuộc collectors nhưng đặt ở đây, vì evidence-store cũng dùng
mà evidence-store không được phụ thuộc collectors. `collectors.models` xuất lại hai enum này.
"""

from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    StringConstraints,
)


class Contract(BaseModel):
    """Lớp gốc của mọi mô hình quy ước: không nhận trường lạ."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True, serialize_by_alias=True)


VN_TZ = timezone(timedelta(hours=7))


def _to_vn(d: datetime) -> datetime:
    return d.astimezone(VN_TZ)


VnDatetime = Annotated[
    AwareDatetime, AfterValidator(_to_vn), PlainSerializer(datetime.isoformat, return_type=str)
]

Actor = Annotated[str, StringConstraints(pattern=r"^(user|system):\S+$")]

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

CaptureTs = Annotated[str, StringConstraints(pattern=r"^\d{8}T\d{6}$")]

NonNegInt = Annotated[int, Field(ge=0)]
NonNegFloat = Annotated[float, Field(ge=0)]


def _check_bbox(b: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    if b[2] < 0 or b[3] < 0:
        raise ValueError("bbox: w and h must be non-negative")
    return b


BBox = Annotated[tuple[float, float, float, float], AfterValidator(_check_bbox)]


def _check_rel_path(p: str) -> str:
    parts = p.split("/")
    if not p or p.startswith("/") or "\\" in p or ".." in parts or "" in parts:
        raise ValueError(f"path must be relative, use '/' and contain no '..': {p!r}")
    return p


RelPath = Annotated[str, AfterValidator(_check_rel_path)]


class Cap(StrEnum):
    """Loại dữ liệu một nguồn thu lấy được. Giá trị dùng trong trường `what` của manifest."""

    VIDEO_METADATA = "video.metadata"
    CHANNEL_METADATA = "channel.metadata"
    CHANNEL_VIDEOS = "channel.videos"
    PLAYLIST_VIDEOS = "playlist.videos"
    TRANSCRIPTS = "video.transcripts"
    COMMENTS = "video.comments"
    THUMBNAILS = "video.thumbnails"
    MEDIA = "video.media"


class CollectLevel(StrEnum):
    """Mức thu."""

    METADATA = "metadata"
    TEXT = "text"
    FULL = "full"


class TranscriptKind(StrEnum):
    UPLOADED = "uploaded"
    AUTO = "auto"
    SUPADATA_AI = "supadata_ai"
    STT = "stt"
