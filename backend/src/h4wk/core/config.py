import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = REPO_ROOT / "config"


def config_dir() -> Path:
    """Thư mục cấu hình: lấy từ H4WK_CONFIG_DIR (test dùng), mặc định là config/ ở gốc repo."""
    env = os.environ.get("H4WK_CONFIG_DIR")
    return Path(env) if env else CONFIG_DIR


def data_dir() -> Path:
    """Thư mục dữ liệu: lấy từ H4WK_DATA_DIR, mặc định là data/ ở gốc repo."""
    env = os.environ.get("H4WK_DATA_DIR")
    return Path(env) if env else REPO_ROOT / "data"
