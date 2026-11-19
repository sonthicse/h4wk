"""Adapter yt-dlp (T9): metadata, phụ đề tiếng Việt, comment, thumbnail, video 720p.

Cần Deno trong PATH (JS runtime để giải challenge của YouTube) và curl_cffi (spike T2).
Các hàm *_from_* là phần chuyển dữ liệu thô sang dữ liệu chung, test được không cần mạng.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError

from h4wk.collectors.base import (
    Blocked,
    CollectorError,
    FetchResult,
    Health,
    NotFound,
    Transient,
    Unsupported,
)
from h4wk.collectors.models import (
    Cap,
    Channel,
    Comment,
    MediaFile,
    Normalized,
    Thumbnail,
    Transcript,
    TranscriptKind,
    TranscriptSegment,
    Video,
)
from h4wk.collectors.targets import Target, TargetKind
from h4wk.core.config import config_dir
from h4wk.core.config_models import SourcesConfig, load_toml

# Video 720p kèm audio; chưa có 720p (video vừa đăng) thì lấy bản tốt nhất hiện có.
MEDIA_FORMAT = "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b"
AUTO_ORIG = "vi-orig"
_VIDEO_CAPS = {Cap.VIDEO_METADATA, Cap.TRANSCRIPTS, Cap.COMMENTS, Cap.THUMBNAILS, Cap.MEDIA}
_CHANNEL_CAPS = {Cap.CHANNEL_METADATA, Cap.CHANNEL_VIDEOS}

_BLOCKED = (
    "sign in to confirm",
    "not a bot",
    "http error 403",
    "http error 429",
    "too many requests",
)
_NOT_FOUND = (
    "video unavailable",
    "private video",
    "has been removed",
    "does not exist",
    "this channel",
    "http error 404",
    "account associated with this video has been",
)


def classify_error(e: Exception) -> CollectorError:
    """Phân loại lỗi yt-dlp theo nội dung thông báo. Lỗi không nhận ra coi là tạm thời."""
    msg = str(e).lower()
    if any(k in msg for k in _BLOCKED):
        return Blocked(str(e))
    if any(k in msg for k in _NOT_FOUND):
        return NotFound(str(e))
    return Transient(str(e))


def _ts(value: int | float | None) -> datetime | None:
    return datetime.fromtimestamp(value, UTC) if value else None


def video_from_info(info: dict[str, Any]) -> Video:
    categories = info.get("categories") or []
    return Video(
        id=info["id"],
        channel_id=info["channel_id"],
        title=info.get("title") or "",
        description=info.get("description") or "",
        tags=info.get("tags") or [],
        category=categories[0] if categories else None,
        duration_s=info.get("duration"),
        published_at=_ts(info.get("timestamp") or info.get("release_timestamp")),
        view_count=info.get("view_count"),
        like_count=info.get("like_count"),
        comment_count=info.get("comment_count"),
        availability=info.get("availability"),
        is_live=info.get("live_status") == "is_live",
    )


def channel_from_info(info: dict[str, Any]) -> Channel:
    thumbs = {t.get("id"): t.get("url") for t in info.get("thumbnails") or []}
    handle = info.get("uploader_id")
    return Channel(
        id=info.get("channel_id") or info["id"],
        handle=handle if handle and handle.startswith("@") else None,
        title=info.get("channel") or info.get("title") or "",
        description=info.get("description") or "",
        subscriber_count=info.get("channel_follower_count"),
        avatar_url=thumbs.get("avatar_uncropped"),
        banner_url=thumbs.get("banner_uncropped"),
    )


def channel_from_video_info(info: dict[str, Any]) -> Channel:
    """Thông tin kênh có sẵn trong metadata của một video (không gọi thêm trang kênh)."""
    handle = info.get("uploader_id")
    return Channel(
        id=info["channel_id"],
        handle=handle if handle and handle.startswith("@") else None,
        title=info.get("channel") or info.get("uploader") or "",
        subscriber_count=info.get("channel_follower_count"),
    )


def resolve_channel(url: str) -> tuple[str, str, str | None]:
    """Đổi link kênh hoặc @handle thành (channel_id, tên kênh, handle)."""
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlist_items": "0"}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except (DownloadError, ExtractorError) as e:
        raise classify_error(e) from e
    handle = info.get("uploader_id")
    return (
        info.get("channel_id") or info["id"],
        info.get("channel") or info.get("title") or "",
        handle if handle and handle.startswith("@") else None,
    )


def video_ids_from_flat(info: dict[str, Any]) -> list[str]:
    return [e["id"] for e in info.get("entries") or [] if e and e.get("id")]


def comments_from_info(info: dict[str, Any]) -> list[Comment]:
    return [
        Comment(
            id=c["id"],
            parent_id=None if c.get("parent", "root") == "root" else c["parent"],
            author_channel_id=c.get("author_id"),
            author_name=c.get("author"),
            text=c.get("text") or "",
            published_at=_ts(c.get("timestamp")),
            like_count=c.get("like_count"),
        )
        for c in info.get("comments") or []
    ]


def subtitle_langs(info: dict[str, Any]) -> tuple[list[str], list[str]]:
    """(phụ đề người đăng tải lên tiếng Việt, phụ đề tự động gốc). Không lấy bản dịch máy."""
    manual = sorted(k for k in info.get("subtitles") or {} if k.startswith("vi"))
    auto = [AUTO_ORIG] if AUTO_ORIG in (info.get("automatic_captions") or {}) else []
    return manual, auto


def _segments_from_json3(data: dict[str, Any]) -> list[TranscriptSegment]:
    events = []
    for ev in data.get("events") or []:
        text = "".join(s.get("utf8", "") for s in ev.get("segs") or []).strip()
        if text:
            events.append((ev["tStartMs"] / 1000, ev.get("dDurationMs", 0) / 1000, text))
    segments = []
    for i, (start, dur, text) in enumerate(events):
        end = start + dur
        if i + 1 < len(events):
            end = min(end, events[i + 1][0])  # phụ đề tự động hiện chồng lên câu sau
        segments.append(TranscriptSegment(start=round(start, 3), end=round(end, 3), text=text))
    return segments


def transcripts_from_dir(workdir: Path, video_id: str) -> list[Transcript]:
    out = []
    for path in sorted(workdir.glob(f"{video_id}.vi*.json3")):
        lang = path.name[len(video_id) + 1 : -len(".json3")]
        kind = TranscriptKind.AUTO if lang == AUTO_ORIG else TranscriptKind.UPLOADED
        data = json.loads(path.read_text(encoding="utf-8"))
        out.append(
            Transcript(
                kind=kind,
                lang="vi" if kind == TranscriptKind.AUTO else lang,
                segments=_segments_from_json3(data),
            )
        )
    return out


def thumbnail_urls(info: dict[str, Any]) -> dict[str, str]:
    """Bản jpg lớn nhất và các khung 0–3.jpg."""
    jpgs = [t for t in info.get("thumbnails") or [] if t["url"].split("?")[0].endswith(".jpg")]
    urls = {}
    if jpgs:
        urls["maxres"] = max(jpgs, key=lambda t: t.get("width") or 0)["url"]
    for n in range(4):
        urls[str(n)] = f"https://i.ytimg.com/vi/{info['id']}/{n}.jpg"
    return urls


class YtDlpCollector:
    name = "ytdlp"
    capabilities = _VIDEO_CAPS | _CHANNEL_CAPS | {Cap.PLAYLIST_VIDEOS}
    version: str | None = yt_dlp.version.__version__

    def __init__(self, cookies_file: str | None = None) -> None:
        self.cookies_file = cookies_file
        self._info_cache: dict[str, dict[str, Any]] = {}

    def _opts(self, **extra: Any) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "socket_timeout": 30,
        }
        if self.cookies_file:
            opts["cookiefile"] = self.cookies_file
        return {**opts, **extra}

    def _extract(self, url: str, download: bool = False, **opts: Any) -> dict[str, Any]:
        with yt_dlp.YoutubeDL(self._opts(**opts)) as ydl:
            info = ydl.extract_info(url, download=download)
            return ydl.sanitize_info(info)

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    def _info(self, target: Target, workdir: Path) -> dict[str, Any]:
        if target.id not in self._info_cache:
            info = self._extract(target.url)
            self._write_json(workdir / f"{target.id}.info.json", info)
            self._info_cache[target.id] = info
        return self._info_cache[target.id]

    def fetch(self, cap: Cap, target: Target, workdir: Path) -> FetchResult:
        if (target.kind == TargetKind.VIDEO) != (cap in _VIDEO_CAPS):
            raise Unsupported(f"{cap} does not apply to {target.kind}")
        try:
            return FetchResult(normalized=self._fetch(cap, target, workdir))
        except (DownloadError, ExtractorError) as e:
            raise classify_error(e) from e

    def _fetch(self, cap: Cap, target: Target, workdir: Path) -> Normalized:
        rel = f"sources/{workdir.name}"
        n: dict[str, Any] = {"schema": "h4wk.normalized/1"}
        if cap == Cap.VIDEO_METADATA:
            info = self._info(target, workdir)
            n["video"] = video_from_info(info)
            n["channel"] = channel_from_video_info(info)
        elif cap == Cap.THUMBNAILS:
            info = self._info(target, workdir)
            n["thumbnails"] = self._download_thumbnails(info, workdir, rel)
        elif cap == Cap.TRANSCRIPTS:
            manual, auto = subtitle_langs(self._info(target, workdir))
            if not manual and not auto:
                raise Unsupported("video has no Vietnamese subtitles")
            self._extract(
                target.url,
                download=True,
                skip_download=True,
                writesubtitles=bool(manual),
                writeautomaticsub=bool(auto),
                subtitleslangs=manual + auto,
                subtitlesformat="json3",
                outtmpl=str(workdir / "%(id)s.%(ext)s"),
            )
            n["transcripts"] = transcripts_from_dir(workdir, target.id)
        elif cap == Cap.COMMENTS:
            info = self._extract(target.url, getcomments=True)
            self._write_json(workdir / f"{target.id}.comments.json", info.get("comments") or [])
            n["comments"] = comments_from_info(info)
        elif cap == Cap.MEDIA:
            info = self._extract(
                target.url,
                download=True,
                format=MEDIA_FORMAT,
                merge_output_format="mp4",
                outtmpl=str(workdir / "%(id)s.%(ext)s"),
            )
            d = (info.get("requested_downloads") or [info])[0]
            n["media"] = [
                MediaFile(
                    kind="video",
                    file=f"{rel}/{Path(d['filepath']).name}",
                    height=d.get("height"),
                    vcodec=d.get("vcodec"),
                    acodec=d.get("acodec"),
                    duration_s=info.get("duration"),
                )
            ]
        else:  # kênh và playlist: chỉ liệt kê, không tải từng video
            url = f"{target.url}/videos" if target.kind != TargetKind.PLAYLIST else target.url
            info = self._extract(url, extract_flat="in_playlist")
            self._write_json(workdir / f"{target.id}.flat.json", info)
            if cap == Cap.CHANNEL_METADATA:
                n["channel"] = channel_from_info(info)
            else:
                n["video_ids"] = video_ids_from_flat(info)
        return Normalized.model_validate(n)

    def _download_thumbnails(
        self, info: dict[str, Any], workdir: Path, rel: str
    ) -> list[Thumbnail]:
        widths = {t["url"]: (t.get("width"), t.get("height")) for t in info.get("thumbnails") or []}
        out = []
        with yt_dlp.YoutubeDL(self._opts()) as ydl:
            for name, url in thumbnail_urls(info).items():
                try:
                    data = ydl.urlopen(url).read()
                except Exception as e:  # thiếu một ảnh khung không làm hỏng cả loại dữ liệu
                    if name == "maxres":
                        raise classify_error(e) from e
                    continue
                (workdir / f"{name}.jpg").write_bytes(data)
                w, h = widths.get(url, (None, None))
                out.append(
                    Thumbnail(name=name, url=url, file=f"{rel}/{name}.jpg", width=w, height=h)
                )
        return out

    def health_check(self) -> Health:
        return Health(ok=True, detail=f"yt-dlp {self.version}")


def from_config() -> YtDlpCollector:
    path = config_dir() / "sources.toml"
    cfg = load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()
    return YtDlpCollector(cookies_file=cfg.sources.ytdlp.cookies_file)
