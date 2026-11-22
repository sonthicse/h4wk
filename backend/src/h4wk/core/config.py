from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


def dotenv() -> dict[str, str]:
    return {k: v for k, v in dotenv_values(REPO_ROOT / ".env").items() if v}


def config_dir() -> Path:
    return CONFIG_DIR


def data_dir() -> Path:
    return DATA_DIR
