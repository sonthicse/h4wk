"""Adapter YouTube Data API v3 (T14): metadata, comment, thumbnail, danh sách video.

Không lấy transcript và video. Danh sách video của kênh lấy qua uploads playlist, không dùng
`search.list` (tốn 100 đơn vị). Key gửi qua header `X-Goog-Api-Key`, không bao giờ đặt trong URL.
Các hàm *_from_* là phần chuyển dữ liệu thô sang dữ liệu chung, test được không cần mạng.
"""

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx2

from h4wk.collectors import quota
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
    Comment,
    Normalized,
    Thumbnail,
    Video,
)
from h4wk.collectors.targets import Target, TargetKind
from h4wk.core import secrets
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Cost

API = "https://www.googleapis.com/youtube/v3"
KEY_NAME = "YOUTUBE_API_KEY"
MAX_LIST_VIDEOS = 200
CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}
_TARGET_KIND = {
    Cap.VIDEO_METADATA: TargetKind.VIDEO,
    Cap.THUMBNAILS: TargetKind.VIDEO,
    Cap.COMMENTS: TargetKind.VIDEO,
    Cap.CHANNEL_METADATA: TargetKind.CHANNEL,
    Cap.CHANNEL_VIDEOS: TargetKind.CHANNEL,
    Cap.PLAYLIST_VIDEOS: TargetKind.PLAYLIST,
}
_DURATION = re.compile(r"^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?)?$")


def parse_duration(value: str | None) -> float | None:
    """Đổi thời lượng ISO 8601 (PT4M13S, P1DT1S) sang giây."""
    if value is None:
        return None
    m = _DURATION.match(value)
    if not m:
        return None
    d, h, mi, s = (float(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _int(v: Any) -> int | None:
    """API trả số dạng chuỗi."""
    return int(v) if v is not None else None


def _ts(v: str | None) -> datetime | None:
    return datetime.fromisoformat(v) if v else None


def video_from_api(item: dict[str, Any]) -> Video:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    return Video(
        id=item["id"],
        channel_id=sn["channelId"],
        title=sn.get("title") or "",
        description=sn.get("description") or "",
        tags=sn.get("tags") or [],
        category=CATEGORIES.get(sn.get("categoryId")),
        duration_s=parse_duration(item.get("contentDetails", {}).get("duration")),
        published_at=_ts(sn.get("publishedAt")),
        view_count=_int(st.get("viewCount")),
        like_count=_int(st.get("likeCount")),
        comment_count=_int(st.get("commentCount")),
        availability=item.get("status", {}).get("privacyStatus"),
        is_live=sn.get("liveBroadcastContent") == "live",
    )


def channel_from_api(item: dict[str, Any]) -> Channel:
    sn = item.get("snippet", {})
    st = item.get("statistics", {})
    handle = sn.get("customUrl")
    thumbs = sn.get("thumbnails") or {}
    avatar = next((thumbs[k]["url"] for k in ("high", "medium", "default") if k in thumbs), None)
    return Channel(
        id=item["id"],
        handle=handle if handle and handle.startswith("@") else None,
        title=sn.get("title") or "",
        description=sn.get("description") or "",
        country=sn.get("country"),
        created_at=_ts(sn.get("publishedAt")),
        subscriber_count=None
        if st.get("hiddenSubscriberCount")
        else _int(st.get("subscriberCount")),
        view_count=_int(st.get("viewCount")),
        video_count=_int(st.get("videoCount")),
        avatar_url=avatar,
        banner_url=item.get("brandingSettings", {}).get("image", {}).get("bannerExternalUrl"),
    )


def _comment(c: dict[str, Any], parent_id: str | None) -> Comment:
    sn = c["snippet"]
    return Comment(
        id=c["id"],
        parent_id=parent_id,
        author_channel_id=(sn.get("authorChannelId") or {}).get("value"),
        author_name=sn.get("authorDisplayName"),
        text=sn.get("textOriginal") or sn.get("textDisplay") or "",
        published_at=_ts(sn.get("publishedAt")),
        like_count=_int(sn.get("likeCount")),
    )


def comments_from_api(
    threads: list[dict[str, Any]], replies: dict[str, list[dict[str, Any]]]
) -> list[Comment]:
    """Comment gốc rồi đến reply của nó. `replies` là reply đã lấy đủ qua comments.list; thread
    không có trong đó thì dùng reply kèm sẵn (tối đa 5) trong response của thread."""
    out: dict[str, Comment] = {}
    for t in threads:
        for c in [_comment(t["snippet"]["topLevelComment"], None)] + [
            _comment(r, t["id"])
            for r in replies.get(t["id"]) or t.get("replies", {}).get("comments", [])
        ]:
            out.setdefault(c.id, c)
    return list(out.values())


def thumbnail_candidates(item: dict[str, Any]) -> list[tuple[str, int | None, int | None]]:
    """Các bản thumbnail API liệt kê, lớn nhất trước."""
    thumbs = (item.get("snippet", {}).get("thumbnails") or {}).values()
    ordered = sorted(thumbs, key=lambda t: t.get("width") or 0, reverse=True)
    return [(t["url"], t.get("width"), t.get("height")) for t in ordered]


def thumbnails_from_api(item: dict[str, Any]) -> dict[str, tuple[str, int | None, int | None]]:
    """Bản lớn nhất và các khung 0–3.jpg (giống ytdlp.thumbnail_urls)."""
    candidates = thumbnail_candidates(item)
    out: dict[str, tuple[str, int | None, int | None]] = {}
    if candidates:
        out["maxres"] = candidates[0]
    for n in range(4):
        out[str(n)] = (f"https://i.ytimg.com/vi/{item['id']}/{n}.jpg", None, None)
    return out


def video_ids_from_pages(pages: list[dict[str, Any]]) -> list[str]:
    ids = [i["contentDetails"]["videoId"] for p in pages for i in p.get("items") or []]
    return ids[:MAX_LIST_VIDEOS]


def _reason(body: dict[str, Any] | None) -> str:
    errors = ((body or {}).get("error") or {}).get("errors") or []
    return errors[0].get("reason", "") if errors else ""


def classify_error(status: int, body: dict[str, Any] | None) -> CollectorError:
    reason = _reason(body)
    message = ((body or {}).get("error") or {}).get("message", "")
    text = f"YouTube API {status} {reason}: {message}"
    if reason in {"quotaExceeded", "dailyLimitExceeded"}:
        return QuotaExceeded(text)
    if reason in {"rateLimitExceeded", "userRateLimitExceeded"} or status == 429 or status >= 500:
        return Transient(text)
    if status == 404 or reason.endswith("NotFound"):
        return NotFound(text)
    return Blocked(text)


class YouTubeApiCollector:
    name = "youtube_api"
    capabilities = set(_TARGET_KIND)
    version: str | None = None

    def __init__(
        self,
        client: httpx2.Client | None = None,
        key: Callable[[], str | None] = lambda: secrets.get(KEY_NAME),
        now: Callable[[], datetime] = lambda: datetime.now(VN_TZ),
    ) -> None:
        self.client = client or httpx2.Client(follow_redirects=True)
        self.key = key
        self.now = now
        self._units = 0
        self._cache: dict[tuple[str, str], dict[str, Any]] = {}

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def _get(
        self, path: str, params: dict[str, Any], empty_on: str | None = None
    ) -> dict[str, Any]:
        """Gọi một endpoint (1 đơn vị quota). Lỗi có reason `empty_on` coi như không có dữ liệu."""
        key = self.key()
        if not key:
            raise Blocked(f"{KEY_NAME} is not set")
        quota.spend(1, self.now())
        self._units += 1
        try:
            r = self.client.get(
                f"{API}/{path}", params=params, headers={"X-Goog-Api-Key": key}, timeout=30
            )
        except (httpx2.TransportError, httpx2.TimeoutException) as e:
            raise Transient(str(e)) from e
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError as e:
                raise Transient("YouTube API returned a non-JSON response") from e
        try:
            body = r.json()
        except ValueError:
            body = None
        if empty_on and _reason(body) == empty_on:
            return {"items": []}
        err = classify_error(r.status_code, body)
        if isinstance(err, QuotaExceeded):
            quota.exhaust(self.now())
        raise err

    def _video(self, target: Target, workdir: Path) -> dict[str, Any]:
        ck = ("video", target.id)
        if ck not in self._cache:
            data = self._get(
                "videos",
                {"part": "snippet,contentDetails,statistics,status", "id": target.id},
            )
            self._write_json(workdir / f"{target.id}.video.json", data)
            if not data.get("items"):
                raise NotFound(f"video {target.id} not found or not public")
            self._cache[ck] = data["items"][0]
        return self._cache[ck]

    def _channel(self, channel_id: str, workdir: Path) -> dict[str, Any]:
        ck = ("channel", channel_id)
        if ck not in self._cache:
            data = self._get(
                "channels",
                {
                    "part": "snippet,statistics,contentDetails,brandingSettings",
                    "id": channel_id,
                },
            )
            self._write_json(workdir / f"{channel_id}.channel.json", data)
            if not data.get("items"):
                raise NotFound(f"channel {channel_id} not found")
            self._cache[ck] = data["items"][0]
        return self._cache[ck]

    def fetch(self, cap: Cap, target: Target, workdir: Path) -> FetchResult:
        if _TARGET_KIND.get(cap) != target.kind:
            raise Unsupported(f"{cap} does not apply to {target.kind}")
        self._units = 0
        normalized = self._fetch(cap, target, workdir)
        return FetchResult(normalized=normalized, cost=Cost(quota_units=self._units))

    def _fetch(self, cap: Cap, target: Target, workdir: Path) -> Normalized:
        n: dict[str, Any] = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            item = self._video(target, workdir)
            n["video"] = video_from_api(item)
            n["channel"] = channel_from_api(self._channel(item["snippet"]["channelId"], workdir))
        elif cap == Cap.THUMBNAILS:
            n["thumbnails"] = self._download_thumbnails(self._video(target, workdir), workdir)
        elif cap == Cap.COMMENTS:
            n["comments"] = self._comments(target, workdir)
        elif cap == Cap.CHANNEL_METADATA:
            n["channel"] = channel_from_api(self._channel(target.id, workdir))
        else:
            playlist = target.id
            if cap == Cap.CHANNEL_VIDEOS:
                playlist = self._channel(target.id, workdir)["contentDetails"]["relatedPlaylists"][
                    "uploads"
                ]
            n["video_ids"] = self._playlist(playlist, target, workdir)
        return Normalized.model_validate(n)

    def _comments(self, target: Target, workdir: Path) -> list[Comment]:
        """Toàn bộ comment: mọi trang thread, reply thiếu thì lấy thêm qua comments.list."""
        base = {"part": "snippet,replies", "videoId": target.id, "maxResults": 100}
        pages = self._pages(
            "commentThreads", base, textFormat="plainText", empty_on="commentsDisabled"
        )
        threads = [t for p in pages for t in p.get("items") or []]
        replies: dict[str, list[dict[str, Any]]] = {}
        reply_pages: dict[str, list[dict[str, Any]]] = {}
        for t in threads:
            inline = len(t.get("replies", {}).get("comments", []))
            if t["snippet"].get("totalReplyCount", 0) > inline:
                rp = self._pages(
                    "comments",
                    {"part": "snippet", "parentId": t["id"], "maxResults": 100},
                    textFormat="plainText",
                )
                reply_pages[t["id"]] = rp
                replies[t["id"]] = [c for p in rp for c in p.get("items") or []]
        self._write_json(
            workdir / f"{target.id}.comments.json", {"threads": pages, "replies": reply_pages}
        )
        return comments_from_api(threads, replies)

    def _pages(
        self,
        path: str,
        params: dict[str, Any],
        limit: int | None = None,
        empty_on: str | None = None,
        **extra: Any,
    ) -> list[dict[str, Any]]:
        """Đọc lần lượt các trang tới khi hết nextPageToken (hoặc đủ `limit` mục)."""
        params = {**params, **extra}
        pages: list[dict[str, Any]] = []
        count = 0
        while True:
            page = self._get(path, params, empty_on)
            pages.append(page)
            count += len(page.get("items") or [])
            token = page.get("nextPageToken")
            if not token or (limit is not None and count >= limit):
                return pages
            params = {**params, "pageToken": token}

    def _playlist(self, playlist_id: str, target: Target, workdir: Path) -> list[str]:
        pages = self._pages(
            "playlistItems",
            {"part": "contentDetails", "playlistId": playlist_id, "maxResults": 50},
            limit=MAX_LIST_VIDEOS,
        )
        self._write_json(workdir / f"{target.id}.playlist.json", pages)
        return video_ids_from_pages(pages)

    def _download_thumbnails(self, item: dict[str, Any], workdir: Path) -> list[Thumbnail]:
        rel = f"sources/{workdir.name}"
        out = []
        for name, (url, w, h) in thumbnails_from_api(item).items():
            tries = thumbnail_candidates(item) if name == "maxres" else [(url, w, h)]
            for url, w, h in tries:
                try:
                    r = self.client.get(url, timeout=30)
                except (httpx2.TransportError, httpx2.TimeoutException) as e:
                    if name == "maxres":
                        raise Transient(str(e)) from e
                    break
                if r.status_code == 200:
                    (workdir / f"{name}.jpg").write_bytes(r.content)
                    file = f"{rel}/{name}.jpg"
                    out.append(Thumbnail(name=name, url=url, file=file, width=w, height=h))
                    break
                if name == "maxres" and (r.status_code >= 500 or (url, w, h) == tries[-1]):
                    err = Transient if r.status_code >= 500 else Blocked
                    raise err(f"thumbnail {name} returned HTTP {r.status_code}")
        return out

    def health_check(self) -> Health:
        if not self.key():
            return Health(False, f"{KEY_NAME} is not set")
        try:
            self._get("videos", {"part": "id", "id": "jNQXAC9IVRw"})
        except CollectorError as e:
            return Health(False, str(e))
        u = quota.usage(self.now())
        return Health(True, f"quota {u.used}/{u.limit} units today")


def from_config() -> YouTubeApiCollector:
    return YouTubeApiCollector()
