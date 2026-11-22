import tomllib
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field

from h4wk.core.types import Cap, CollectLevel, Contract


def _no_duplicates[T](items: list[T]) -> list[T]:
    if len(items) != len(set(items)):
        raise ValueError("list has duplicate items")
    return items


class SourceName(StrEnum):
    YTDLP = "ytdlp"
    YOUTUBE_API = "youtube_api"
    SUPADATA = "supadata"


class SourceConfig(Contract):
    enabled: bool = True
    fault_injection: bool = False


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
    threads_per_channel: int = Field(default=1, ge=1, le=8)


class SourcesConfig(Contract):
    sources: SourcesSection = SourcesSection()
    priority: dict[Cap, Annotated[list[SourceName], AfterValidator(_no_duplicates)]] = {}
    collect: CollectSettings = CollectSettings()
    watchlist: WatchlistSettings = WatchlistSettings()


class WatchChannel(Contract):
    id: str = Field(pattern=r"^w_\d{3,}$")
    channel_id: str = Field(min_length=1)
    handle: str | None = None
    title: str = ""
    level: CollectLevel = CollectLevel.FULL
    enabled: bool = True


def _unique_channels(items: list[WatchChannel]) -> list[WatchChannel]:
    for field in ("id", "channel_id"):
        values = [getattr(c, field) for c in items]
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {field} in watchlist")
    return items


class WatchlistConfig(Contract):
    channels: Annotated[list[WatchChannel], AfterValidator(_unique_channels)] = []


def load_toml[M: BaseModel](path: Path, model: type[M]) -> M:
    return model.model_validate(tomllib.loads(path.read_text(encoding="utf-8")))
