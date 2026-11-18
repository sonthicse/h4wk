"""Hợp đồng C5: định dạng config/sources.toml, ai.toml, analysis.toml (SPEC 10.1).

File cấu hình không chứa secret. API key nằm trong .env hoặc data/secrets.json.
"""

import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, Field, HttpUrl, model_validator

from h4wk.core.types import Cap, Contract, TranscriptKind


def _no_duplicates[T](items: list[T]) -> list[T]:
    if len(items) != len(set(items)):
        raise ValueError("danh sách có phần tử trùng")
    return items


# ---------------------------------------------------------------- sources.toml


class SourceName(StrEnum):
    YTDLP = "ytdlp"
    YOUTUBE_API = "youtube_api"
    SUPADATA = "supadata"


class SourceConfig(Contract):
    enabled: bool = True
    fault_injection: bool = False  # giả lập nguồn bị chặn, cho test và demo


class YtDlpConfig(SourceConfig):
    cookies_file: str | None = None


class SourcesSection(Contract):
    ytdlp: YtDlpConfig = YtDlpConfig()
    youtube_api: SourceConfig = SourceConfig()
    supadata: SourceConfig = SourceConfig()


class CollectSettings(Contract):
    playlist_max_videos: int = Field(default=50, ge=1)


class WatchlistSettings(Contract):
    check_interval_min: int = Field(default=2, ge=1)
    initial_videos: int = Field(default=10, ge=0)


class SourcesConfig(Contract):
    sources: SourcesSection = SourcesSection()
    # Thứ tự ưu tiên nguồn cho từng loại dữ liệu.
    priority: dict[Cap, Annotated[list[SourceName], AfterValidator(_no_duplicates)]] = {}
    collect: CollectSettings = CollectSettings()
    watchlist: WatchlistSettings = WatchlistSettings()


# --------------------------------------------------------------------- ai.toml


class AiTask(StrEnum):
    CLASSIFY = "analysis.classify"
    CLASSIFY_COMMENT = "analysis.classify_comment"
    VISION = "media.vision"


class ModelCaps(Contract):
    vision: bool = False  # đọc được ảnh
    structured: bool = False  # hỗ trợ JSON schema hoặc tool calling


class ProviderConfig(Contract):
    type: Literal["anthropic", "openai_compat", "gemini"]
    base_url: HttpUrl | None = None  # bắt buộc với openai_compat
    models: dict[str, ModelCaps]

    @model_validator(mode="after")
    def _base_url(self) -> Self:
        if self.type == "openai_compat" and self.base_url is None:
            raise ValueError("provider openai_compat phải có base_url")
        return self


class Route(Contract):
    provider: str
    model: str


class AiConfig(Contract):
    providers: dict[str, ProviderConfig]
    # Tác vụ AI → danh sách (provider, model) theo thứ tự ưu tiên.
    tasks: dict[AiTask, Annotated[list[Route], Field(min_length=1)]] = {}

    @model_validator(mode="after")
    def _routes(self) -> Self:
        for task, routes in self.tasks.items():
            for r in routes:
                provider = self.providers.get(r.provider)
                if provider is None:
                    raise ValueError(f"{task}: provider {r.provider!r} chưa được khai báo")
                caps = provider.models.get(r.model)
                if caps is None:
                    raise ValueError(f"{task}: model {r.model!r} chưa có trong {r.provider}")
                if task == AiTask.VISION and not caps.vision:
                    raise ValueError(f"{task}: {r.provider}/{r.model} không đọc được ảnh")
        return self


# --------------------------------------------------------------- analysis.toml


class FaceSettings(Contract):
    enabled: bool = True


class RefImageSettings(Contract):
    enabled: bool = True
    threshold: float | None = Field(default=None, ge=0, le=1)  # None: dùng mặc định của model


class CommentSettings(Contract):
    batch_size: int = Field(default=30, ge=20, le=50)
    max_per_video: int | None = Field(default=None, ge=1)  # None: không giới hạn


class KeyframeSettings(Contract):
    phash_threshold: int = Field(default=6, ge=0, le=64)
    tile_threshold: float = Field(default=2.0, ge=0, le=255)


class AnalysisConfig(Contract):
    keyframes: KeyframeSettings = KeyframeSettings()
    transcript_priority: Annotated[list[TranscriptKind], AfterValidator(_no_duplicates)] = [
        TranscriptKind.UPLOADED,
        TranscriptKind.STT,
        TranscriptKind.AUTO,
        TranscriptKind.SUPADATA_AI,
    ]
    face: FaceSettings = FaceSettings()
    ref_image: RefImageSettings = RefImageSettings()
    comments: CommentSettings = CommentSettings()


def load_toml[M: BaseModel](path: Path, model: type[M]) -> M:
    """Đọc một file cấu hình và kiểm tra theo C5."""
    return model.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
