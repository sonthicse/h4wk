"""Đọc định tuyến AI từ cấu hình C5."""

from pathlib import Path

from h4wk.core.config import CONFIG_DIR, config_dir
from h4wk.core.config_models import AiConfig, load_toml

AI_CONFIG_PATH = CONFIG_DIR / "ai.toml"  # file trong repo; lúc chạy dùng ai_config_path()


def ai_config_path() -> Path:
    return config_dir() / "ai.toml"


def load_ai_config(path: Path | None = None) -> AiConfig:
    return load_toml(path or ai_config_path(), AiConfig)
