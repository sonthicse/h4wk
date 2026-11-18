"""Đường dẫn dùng chung: gốc repo, thư mục dữ liệu, thư mục cấu hình."""

import os
from pathlib import Path

# backend/src/h4wk/core/config.py -> parents[4] là gốc repo (cần cài editable, mặc định của uv)
REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = REPO_ROOT / "config"


def data_dir() -> Path:
    """Thư mục dữ liệu: lấy từ H4WK_DATA_DIR, mặc định là data/ ở gốc repo."""
    env = os.environ.get("H4WK_DATA_DIR")
    return Path(env) if env else REPO_ROOT / "data"
