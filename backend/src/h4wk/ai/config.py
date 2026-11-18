"""Đọc định tuyến AI từ cấu hình C5."""

from pathlib import Path

from h4wk.core.config import CONFIG_DIR
from h4wk.core.config_models import AiConfig, load_toml

AI_CONFIG_PATH = CONFIG_DIR / "ai.toml"


def load_ai_config(path: Path = AI_CONFIG_PATH) -> AiConfig:
    return load_toml(path, AiConfig)
