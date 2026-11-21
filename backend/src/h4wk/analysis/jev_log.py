"""Nhật ký request Jev (`data/jev_calls.jsonl`) và tổng hợp usage.

Mỗi request logic một dòng, ghi nối. Không ghi nội dung văn bản, ảnh hay key.
"""

import json
import re
import threading
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ

_LOCK = threading.Lock()
_LOCAL = threading.local()
RECENT_ERRORS = 5
PERIODS = {"today": 1, "7d": 7, "30d": 30}


def path():
    return data_dir() / "jev_calls.jsonl"


def source_of(kind: str) -> str:
    """Tiêu đề và mô tả gộp một nguồn `metadata`."""
    return "metadata" if kind in {"title", "description"} else kind


def count_retry() -> None:
    """Gọi từ `_call` mỗi lần gặp 429 rồi thử lại; request logic đọc lại bằng `take_retries`."""
    _LOCAL.retries = getattr(_LOCAL, "retries", 0) + 1


def take_retries() -> int:
    retries = getattr(_LOCAL, "retries", 0)
    _LOCAL.retries = 0
    return retries


def error_status(text: str) -> str:
    """Chỉ giữ mã HTTP; thông báo lỗi khác có thể chứa đường dẫn hoặc nội dung."""
    match = re.match(r"HTTP \d{3}\b", text)
    return match[0] if match else "error"


def record(
    *,
    video_id: str | None,
    capture: str | None,
    run_id: str | None,
    source_kind: str,
    images: int,
    reply: dict[str, Any] | None,
    kept: bool,
    status: str,
    retries_429: int,
) -> None:
    usage = (reply or {}).get("usage")
    if not isinstance(usage, dict):
        usage = {}

    def tokens(name):
        value = usage.get(name)
        return value if type(value) is int and value >= 0 else None

    line = {
        "at": datetime.now(VN_TZ).isoformat(),
        "video_id": video_id,
        "capture": capture,
        "run_id": run_id,
        "source_kind": source_kind,
        "images": images,
        "input_tokens": tokens("input_tokens"),
        "output_tokens": tokens("output_tokens"),
        "kept": kept,
        "status": status,
        "retries_429": retries_429,
    }
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK, target.open("a", encoding="utf-8") as file:
        file.write(json.dumps(line, ensure_ascii=False) + "\n")


def read(since: datetime, until: datetime) -> list[dict[str, Any]]:
    """Các dòng trong khoảng `since` đến `until`; bỏ qua dòng hỏng."""
    target = path()
    if not target.is_file():
        return []
    rows = []
    for text in target.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(text)
            if since <= datetime.fromisoformat(row["at"]) <= until:
                rows.append(row)
        except (ValueError, KeyError, TypeError):
            continue
    return rows


def period_start(period: str, now: datetime) -> datetime:
    midnight = now.astimezone(VN_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    return midnight - timedelta(days=PERIODS[period] - 1)


def month_start(now: datetime) -> datetime:
    return now.astimezone(VN_TZ).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = Counter()
    by_source: dict[str, Counter] = {}
    for row in rows:
        error = row.get("status") != "ok"
        parts = {
            "requests": 1,
            "kept": int(bool(row.get("kept"))),
            "errors": int(error),
        }
        source = by_source.setdefault(source_of(row.get("source_kind", "")), Counter())
        for key in ("input_tokens", "output_tokens"):
            value = row.get(key)
            if type(value) is int and value >= 0:
                parts[key] = value
        for key, value in parts.items():
            total[key] += value
            source[key] += value
        total["image_requests"] += int((row.get("images") or 0) > 0)
        total["retries_429"] += row.get("retries_429") or 0
    return {"total": total, "by_source": by_source}
