"""Ghi TOML cho file cấu hình C5 (Python chỉ có sẵn bộ đọc tomllib). Chỉ hỗ trợ kiểu C5 dùng:
bảng lồng nhau, chuỗi, số, bool, mảng giá trị đơn và mảng bảng nội tuyến. Comment không giữ lại."""

import json
import re
from typing import Any

_BARE = re.compile(r"^[A-Za-z0-9_-]+$")


def _key(k: str) -> str:
    return k if _BARE.match(k) else json.dumps(k, ensure_ascii=False)


def _value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int | float):
        return repr(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, list):
        return "[" + ", ".join(_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{_key(k)} = {_value(x)}" for k, x in v.items()) + " }"
    raise TypeError(f"cannot write {type(v).__name__} to TOML")


def dumps(data: dict[str, Any]) -> str:
    out: list[str] = []

    def table(path: list[str], d: dict[str, Any]) -> None:
        scalars = {k: v for k, v in d.items() if not isinstance(v, dict) and v is not None}
        tables = {k: v for k, v in d.items() if isinstance(v, dict)}
        if path and (scalars or not tables):
            out.append(f"[{'.'.join(_key(p) for p in path)}]")
        for k, v in scalars.items():
            out.append(f"{_key(k)} = {_value(v)}")
        if path and (scalars or not tables):
            out.append("")
        for k, v in tables.items():
            table([*path, k], v)

    table([], data)
    return "\n".join(out).rstrip() + "\n"
