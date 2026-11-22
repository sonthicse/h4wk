"""Đường dẫn cố định và file .env. Dữ liệu luôn ở data/, cấu hình luôn ở config/ của gốc repo;
tài khoản và API key chỉ đọc từ file .env, không đọc biến môi trường."""

from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = REPO_ROOT / "config"
DATA_DIR = REPO_ROOT / "data"


def dotenv() -> dict[str, str]:
    """Giá trị trong file .env (bỏ giá trị rỗng). Test thay hàm này bằng giá trị cố định."""
    return {k: v for k, v in dotenv_values(REPO_ROOT / ".env").items() if v}


# Hai hàm dưới đọc biến của module lúc gọi, để test đổi CONFIG_DIR, DATA_DIR sang thư mục tạm.
def config_dir() -> Path:
    return CONFIG_DIR


def data_dir() -> Path:
    return DATA_DIR
