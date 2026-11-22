from pathlib import Path

from pydantic import BaseModel

from h4wk.core import tomlw
from h4wk.core.config import config_dir
from h4wk.core.config_models import SourcesConfig, load_toml

SOURCE_KEYS: dict[str, str | None] = {
    "ytdlp": None,
    "youtube_api": "YOUTUBE_API_KEY",
    "supadata": "SUPADATA_API_KEY",
}


def sources_path() -> Path:
    return config_dir() / "sources.toml"


def load_sources() -> SourcesConfig:
    path = sources_path()
    return load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()


def _write(path: Path, model: BaseModel) -> None:
    text = tomlw.dumps(model.model_dump(mode="json", exclude_none=True, by_alias=True))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def save_sources(cfg: SourcesConfig) -> None:
    _write(sources_path(), cfg)
