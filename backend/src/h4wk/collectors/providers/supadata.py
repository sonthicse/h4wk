"""Adapter Supadata (T15): transcript và metadata video, dùng khi yt-dlp bị chặn.

Transcript lấy phụ đề tiếng Việt có sẵn trước (mode native); không có thì nhờ AI của Supadata
tạo (mode generate, có thể phải chờ job). Supadata không cho biết phụ đề YouTube là `uploaded`
hay `auto`, nên mọi transcript từ Supadata đều gắn `supadata_ai`.
Credit trong kỳ thanh toán hỏi Supadata qua GET /me (nhớ 5 phút), không tự đếm; credit của từng
lần gọi lấy từ header `x-billable-requests` và ghi vào manifest. Key gửi qua header `x-api-key`.
"""

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx2

from h4wk.collectors.base import (
    Blocked,
    CollectorError,
    FetchResult,
    Health,
    NotFound,
    QuotaExceeded,
    Transient,
    Unsupported,
)
from h4wk.collectors.models import (
    Cap,
    Channel,
    Normalized,
    Transcript,
    TranscriptKind,
    TranscriptSegment,
    Video,
)
from h4wk.collectors.targets import Target, TargetKind
from h4wk.core import secrets
from h4wk.evidence.models import Cost

API = "https://api.supadata.ai/v1"
KEY_NAME = "SUPADATA_API_KEY"
POLL_INTERVAL = 1.0
JOB_TIMEOUT = 600.0  # giây
ME_TTL = 300.0


def _ts(v: str | None) -> datetime | None:
    return datetime.fromisoformat(v) if v else None


def video_from_supadata(d: dict[str, Any]) -> Video:
    return Video(
        id=d["id"],
        channel_id=d["channel"]["id"],
        title=d.get("title") or "",
        description=d.get("description") or "",
        tags=d.get("tags") or [],
        duration_s=d.get("duration"),
        published_at=_ts(d.get("uploadDate")),
        view_count=d.get("viewCount"),
        like_count=d.get("likeCount"),
    )


def channel_from_supadata(d: dict[str, Any]) -> Channel:
    return Channel(id=d["channel"]["id"], title=d["channel"]["name"])


def transcript_from_supadata(d: dict[str, Any]) -> Transcript:
    rows = [
        (c["offset"] / 1000, (c["offset"] + c.get("duration", 0)) / 1000, c["text"].strip())
        for c in d.get("content") or []
    ]
    rows = [r for r in rows if r[2]]
    segments = []
    for i, (start, end, text) in enumerate(rows):
        if i + 1 < len(rows):
            end = min(end, rows[i + 1][0])  # phụ đề tự động hay hiện chồng lên câu sau
        segments.append(TranscriptSegment(start=round(start, 3), end=round(end, 3), text=text))
    return Transcript(
        kind=TranscriptKind.SUPADATA_AI, lang=d.get("lang") or "vi", segments=segments
    )


def classify_error(status: int, body: dict[str, Any] | None) -> CollectorError:
    code = (body or {}).get("error") or ""
    text = f"Supadata {status} {code}: {(body or {}).get('message', '')}"
    if code == "transcript-unavailable" or status == 206:
        return Unsupported(text)
    if code == "not-found" or status == 404:
        return NotFound(text)
    if code == "limit-exceeded" or status == 429:
        return QuotaExceeded(text)
    if code in {"internal-error", "upstream-error"} or status >= 500:
        return Transient(text)
    return Blocked(text)


@dataclass(frozen=True)
class CreditUsage:
    used: int
    limit: int
    plan: str


class SupadataCollector:
    name = "supadata"
    capabilities = {Cap.TRANSCRIPTS, Cap.VIDEO_METADATA}
    version: str | None = None

    def __init__(
        self,
        client: httpx2.Client | None = None,
        key: Callable[[], str | None] = lambda: secrets.get(KEY_NAME),
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client or httpx2.Client(follow_redirects=True)
        self.key = key
        self.sleep = sleep
        self.monotonic = monotonic
        self._credits = 0

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def _get(
        self, path: str, params: dict[str, Any] | None = None, timeout: float = 30
    ) -> tuple[int, dict[str, Any]]:
        key = self.key()  # đọc mỗi lần để đổi key ở Settings có hiệu lực ngay
        if not key:
            raise Blocked(f"{KEY_NAME} is not set")
        try:
            r = self.client.get(
                f"{API}/{path}", params=params, headers={"x-api-key": key}, timeout=timeout
            )
        except (httpx2.TransportError, httpx2.TimeoutException) as e:
            raise Transient(str(e)) from e
        try:
            self._credits += int(r.headers.get("x-billable-requests", 0))
        except ValueError:
            pass
        try:
            body = r.json()
        except ValueError:
            body = None
        if r.status_code in (200, 202):
            if body is None:
                raise Transient("Supadata returned a non-JSON response")
            return r.status_code, body
        raise classify_error(r.status_code, body)

    def fetch(self, cap: Cap, target: Target, workdir: Path) -> FetchResult:
        if target.kind != TargetKind.VIDEO:
            raise Unsupported(f"{cap} does not apply to {target.kind}")
        self._credits = 0
        normalized = self._fetch(cap, target, workdir)
        return FetchResult(normalized=normalized, cost=Cost(credits=self._credits))

    def _fetch(self, cap: Cap, target: Target, workdir: Path) -> Normalized:
        n: dict[str, Any] = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            # /youtube/video bị đánh dấu deprecated, nhưng /metadata không trả channel id mà C2
            # bắt buộc, nên vẫn dùng.
            _, d = self._get("youtube/video", {"id": target.id})
            self._write_json(workdir / f"{target.id}.video.json", d)
            n["video"] = video_from_supadata(d)
            n["channel"] = channel_from_supadata(d)
        else:
            n["transcripts"] = [transcript_from_supadata(self._transcript(target, workdir))]
        return Normalized.model_validate(n)

    def _transcript(self, target: Target, workdir: Path) -> dict[str, Any]:
        base = {"url": target.url, "text": "false"}
        try:
            _, d = self._get("transcript", {**base, "lang": "vi", "mode": "native"})
            self._write_json(workdir / f"{target.id}.transcript.native.json", d)
            if str(d.get("lang", "")).startswith("vi") and d.get("content"):
                return d
        except Unsupported:
            pass  # không có phụ đề: nhờ AI tạo
        status, d = self._get("transcript", {**base, "mode": "generate"})
        if status == 202:
            job_id = d.get("jobId")
            if not job_id:
                raise Blocked("Supadata returned 202 without jobId")
            d = self._wait_job(job_id)
        self._write_json(workdir / f"{target.id}.transcript.generate.json", d)
        if not d.get("content"):
            raise Unsupported("Supadata detected no speech")
        return d

    def _wait_job(self, job_id: str) -> dict[str, Any]:
        # Hết hạn là Blocked, không phải Transient: tránh gửi lại job generate tốn credit.
        start = self.monotonic()
        while True:
            self.sleep(POLL_INTERVAL)
            try:
                _, d = self._get(f"transcript/{job_id}")
            except Transient:
                # Lỗi mạng thoáng qua khi poll: thử lại ở vòng sau. Ném ra thì orchestrator gửi
                # lại cả fetch và tạo thêm một job generate tốn credit.
                d = {}
            if d.get("status") == "completed":
                return d
            if d.get("status") == "failed":
                raise Blocked(f"Supadata job failed: {d.get('error')}")
            if self.monotonic() - start > JOB_TIMEOUT:
                raise Blocked(f"Supadata job did not finish within {int(JOB_TIMEOUT)} s")

    def me(self) -> CreditUsage:
        _, d = self._get("me", timeout=5)
        return CreditUsage(used=d["usedCredits"], limit=d["maxCredits"], plan=d["plan"])

    def health_check(self) -> Health:
        if not self.key():
            return Health(False, f"{KEY_NAME} is not set")
        try:
            u = self.me()
        except CollectorError as e:
            return Health(False, str(e))
        return Health(True, f"{u.plan}: {u.used}/{u.limit} credits this billing period")


_me_cache: dict[str, tuple[float, CreditUsage | None]] = {}  # key → (thời điểm, kết quả)


def credits_usage(collector: SupadataCollector | None = None) -> CreditUsage | None:
    """Credit đã dùng trong kỳ thanh toán, hỏi Supadata qua /me và nhớ 5 phút; lỗi hoặc chưa có
    key thì None."""
    c = collector or SupadataCollector()
    key = c.key()
    if not key:
        return None
    now = time.monotonic()
    if key in _me_cache and now - _me_cache[key][0] < ME_TTL:
        return _me_cache[key][1]
    try:
        result: CreditUsage | None = c.me()
    except CollectorError:
        result = None
    _me_cache[key] = (now, result)
    return result


def from_config() -> SupadataCollector:
    return SupadataCollector()
