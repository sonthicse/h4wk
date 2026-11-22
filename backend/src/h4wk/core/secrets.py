import json
import os
from typing import Literal

from pydantic import BaseModel

from h4wk.core import config
from h4wk.core.config import data_dir


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


def all_keys() -> dict[str, str]:
    return {**config.dotenv(), **_load()}


def get(name: str) -> str | None:
    return all_keys().get(name)


def put(name: str, value: str) -> None:
    values = _load()
    values[name] = value
    _save(values)


def delete(name: str) -> bool:
    values = _load()
    if values.pop(name, None) is None:
        return False
    _save(values)
    return True


def mask(value: str) -> str:
    return f"{value[:4]}…{value[-4:]}" if len(value) >= 12 else "…" + value[-2:]


def info(name: str) -> KeyInfo:
    stored = _load().get(name)
    if stored:
        return KeyInfo(set=True, masked=mask(stored), origin="settings")
    env = config.dotenv().get(name)
    if env:
        return KeyInfo(set=True, masked=mask(env), origin="env")
    return KeyInfo(set=False, masked=None, origin=None)
