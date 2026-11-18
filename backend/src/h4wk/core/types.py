"""Kiểu dùng chung cho các hợp đồng C1–C5.

Các enum `Cap` và `CollectLevel` thuộc C2 nhưng đặt ở đây, vì C1 (evidence-store) cũng dùng
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
    """Lớp gốc của mọi mô hình hợp đồng: không nhận trường lạ."""

    model_config = ConfigDict(extra="forbid", validate_by_name=True, serialize_by_alias=True)


# Giờ Việt Nam. Việt Nam không đổi giờ theo mùa nên dùng độ lệch cố định.
VN_TZ = timezone(timedelta(hours=7))


def _to_vn(d: datetime) -> datetime:
    return d.astimezone(VN_TZ)


# Thời gian luôn có múi giờ, được đổi sang giờ Việt Nam, ghi ra ISO-8601 kèm +07:00 (SPEC §6).
VnDatetime = Annotated[
    AwareDatetime, AfterValidator(_to_vn), PlainSerializer(datetime.isoformat, return_type=str)
]

# Người thực hiện: `user:<username>` hoặc `system:<rule>`.
Actor = Annotated[str, StringConstraints(pattern=r"^(user|system):\S+$")]

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

# Tên thư mục bản thu theo giờ Việt Nam, ví dụ 20261118T154530.
CaptureTs = Annotated[str, StringConstraints(pattern=r"^\d{8}T\d{6}$")]

NonNegInt = Annotated[int, Field(ge=0)]
NonNegFloat = Annotated[float, Field(ge=0)]


def _check_bbox(b: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    if b[2] < 0 or b[3] < 0:
        raise ValueError("bbox: w và h phải không âm")
    return b


# Khung bao [x, y, w, h] theo pixel.
BBox = Annotated[tuple[float, float, float, float], AfterValidator(_check_bbox)]


def _check_rel_path(p: str) -> str:
    parts = p.split("/")
    if not p or p.startswith("/") or "\\" in p or ".." in parts or "" in parts:
        raise ValueError(f"đường dẫn phải tương đối, dùng '/', không có '..': {p!r}")
    return p


# Đường dẫn tương đối bên trong một thư mục bản thu hoặc thư mục phái sinh.
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
    """Mức thu (SPEC 10.7)."""

    METADATA = "metadata"
    TEXT = "text"
    FULL = "full"


class TranscriptKind(StrEnum):
    UPLOADED = "uploaded"
    AUTO = "auto"
    SUPADATA_AI = "supadata_ai"
    STT = "stt"
