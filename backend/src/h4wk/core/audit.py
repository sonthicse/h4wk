"""Nhật ký thao tác (SPEC 10.1): mỗi thao tác ghi thêm một dòng JSON, kể cả khi thất bại."""

import json
from datetime import datetime
from typing import Any, Literal

from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ


def log(
    actor: str,
    action: str,
    target: str | None,
    detail: dict[str, Any] | None = None,
    status: Literal["ok", "error"] = "ok",
) -> None:
    """Ghi một dòng vào data/log/audit.jsonl."""
    path = data_dir() / "log" / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "at": datetime.now(VN_TZ).isoformat(),
        "actor": actor,
        "action": action,
        "target": target,
        "detail": detail or {},
        "status": status,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
