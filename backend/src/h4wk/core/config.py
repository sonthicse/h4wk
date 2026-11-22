"""Đường dẫn dùng chung và file .env. Cấu hình của máy (thư mục dữ liệu, tài khoản, API key,
model STT) chỉ đọc từ file .env ở gốc repo, không đọc biến môi trường."""

from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[4]
CONFIG_DIR = REPO_ROOT / "config"


def dotenv() -> dict[str, str]:
    """Giá trị trong file .env (bỏ giá trị rỗng). Test thay hàm này bằng giá trị cố định."""
    return {k: v for k, v in dotenv_values(REPO_ROOT / ".env").items() if v}


def config_dir() -> Path:
    """Thư mục cấu hình: H4WK_CONFIG_DIR trong .env, mặc định là config/ ở gốc repo."""
    value = dotenv().get("H4WK_CONFIG_DIR")
    return Path(value) if value else CONFIG_DIR


def data_dir() -> Path:
    """Thư mục dữ liệu: H4WK_DATA_DIR trong .env, mặc định là data/ ở gốc repo."""
    value = dotenv().get("H4WK_DATA_DIR")
    return Path(value) if value else REPO_ROOT / "data"
