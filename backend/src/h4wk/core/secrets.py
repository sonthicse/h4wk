"""Secret (API key). Đặt từ Settings thì lưu ở data/secrets.json (quyền 0600) và được ưu tiên
hơn biến môi trường và .env. API chỉ trả bản che."""

import json
import os
from typing import Literal

from dotenv import dotenv_values
from pydantic import BaseModel

from h4wk.core.config import REPO_ROOT, data_dir


class KeyInfo(BaseModel):
    set: bool
    masked: str | None
    origin: Literal["settings", "env"] | None


def _path():
    return data_dir() / "secrets.json"


def _load() -> dict[str, str]:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def _save(values: dict[str, str]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2)
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def env_values() -> dict[str, str]:
    """.env rồi biến môi trường (biến môi trường thắng)."""
    dot = {k: v for k, v in dotenv_values(REPO_ROOT / ".env").items() if v}
    return {**dot, **{k: v for k, v in os.environ.items() if v}}


def all_keys() -> dict[str, str]:
    """Mọi secret đang có hiệu lực: secrets.json thắng .env và biến môi trường."""
    return {**env_values(), **_load()}


def get(name: str) -> str | None:
    return all_keys().get(name)


def put(name: str, value: str) -> None:
    values = _load()
    values[name] = value
    _save(values)


def delete(name: str) -> None:
    values = _load()
    if values.pop(name, None) is not None:
        _save(values)


def mask(value: str) -> str:
    return f"{value[:4]}…{value[-4:]}" if len(value) >= 12 else "…" + value[-2:]


def info(name: str) -> KeyInfo:
    stored = _load().get(name)
    if stored:
        return KeyInfo(set=True, masked=mask(stored), origin="settings")
    env = env_values().get(name)
    if env:
        return KeyInfo(set=True, masked=mask(env), origin="env")
    return KeyInfo(set=False, masked=None, origin=None)
