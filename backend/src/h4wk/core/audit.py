"""Nhật ký thao tác (SPEC 10.1): mỗi thao tác ghi thêm một dòng JSON, kể cả khi thất bại."""

import json
from datetime import datetime
from typing import Any, Literal

from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ


def log(
    case_id: str | None,
    actor: str,
    action: str,
    target: str | None,
    detail: dict[str, Any] | None = None,
    status: Literal["ok", "error"] = "ok",
) -> None:
    """Ghi vào audit của case; thao tác không thuộc case nào ghi vào system audit."""
    root = data_dir()
    path = (
        root / "cases" / case_id / "log" / "audit.jsonl"
        if case_id
        else root / "log" / "system_audit.jsonl"
    )
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
