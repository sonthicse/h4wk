"""Spike T2 phần 2 và 3: đo độ trễ của RSS và của YouTube API (playlistItems).

Poll RSS của các kênh mỗi 30 giây. Nếu .env có YOUTUBE_API_KEY thì poll thêm
playlistItems của uploads playlist (đọc lại .env mỗi vòng, nên thêm key giữa chừng được).

Độ trễ = thời điểm video xuất hiện lần đầu - thời điểm đăng (`published`/`videoPublishedAt`).
Thời điểm nhận = header `Date` + `Age` của YouTube. RSS được cache 15 phút (max-age=900) trên
nhiều máy chủ, nên `Date` chỉ là lúc bản cache được tạo; `Age` cho biết bản đó đã cũ bao lâu.
Video mới được kiểm tra bằng yt-dlp (chỉ metadata): độ phân giải lớn nhất, có phụ đề vi-orig chưa.

Chạy từ gốc repo:
    uv run --no-project --with 'yt-dlp[default,curl-cffi]' \\
        python docs/spikes/feed_latency.py CHANNEL_ID [CHANNEL_ID ...]

Ghi sự kiện vào .tmp/spike-feed/events.jsonl. Script dùng một lần cho spike.
"""

import json
import os
import re
import sys
import threading
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

import yt_dlp

OUT = Path(".tmp/spike-feed")
LOG = OUT / "events.jsonl"
INTERVAL = 30
RECHECK_AFTER = 15 * 60
_lock = threading.Lock()


def log(event: dict) -> None:
    event["local"] = datetime.now(UTC).isoformat()
    with _lock, LOG.open("a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
        f.flush()


def api_key() -> str | None:
    env = Path(".env")
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("YOUTUBE_API_KEY="):
                return line.split("=", 1)[1].strip() or None
    return os.environ.get("YOUTUBE_API_KEY")


def get(url: str) -> tuple[str, datetime, int]:
    """Trả về nội dung, thời điểm nhận theo server (Date + Age) và tuổi bản cache (giây)."""
    with urllib.request.urlopen(url, timeout=20) as resp:
        body = resp.read().decode()
        age = int(resp.headers.get("Age") or 0)
        server_time = parsedate_to_datetime(resp.headers["Date"]) + timedelta(seconds=age)
    return body, server_time, age


def poll_rss(channel: str) -> tuple[dict[str, str], datetime, int]:
    body, t, age = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel}")
    ids = re.findall(r"<yt:videoId>([^<]+)</yt:videoId>", body)
    pubs = re.findall(r"<entry>.*?<published>([^<]+)</published>", body, re.S)
    return dict(zip(ids, pubs, strict=True)), t, age


def poll_api(channel: str, key: str) -> tuple[dict[str, str], datetime, int]:
    q = urllib.parse.urlencode(
        {"part": "contentDetails", "playlistId": "UU" + channel[2:], "maxResults": 10, "key": key}
    )
    body, t, age = get(f"https://www.googleapis.com/youtube/v3/playlistItems?{q}")
    items = json.loads(body)["items"]
    return (
        {
            i["contentDetails"]["videoId"]: i["contentDetails"].get("videoPublishedAt", "")
            for i in items
        },
        t,
        age,
    )


def ytdlp_check(video_id: str, label: str) -> None:
    """Chỉ đọc metadata: đã có bản 720p và phụ đề vi-orig chưa."""
    opts = {"quiet": True, "no_warnings": True, "socket_timeout": 15, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        heights = [f.get("height") or 0 for f in info.get("formats") or []]
        log(
            {
                "type": "ytdlp",
                "check": label,
                "video": video_id,
                "max_height": max(heights, default=0),
                "vi_orig": "vi-orig" in (info.get("automatic_captions") or {}),
                "manual_vi": [k for k in (info.get("subtitles") or {}) if k.startswith("vi")],
                "live_status": info.get("live_status"),
            }
        )
    except Exception as e:
        log({"type": "ytdlp", "check": label, "video": video_id, "error": str(e)[:300]})


def schedule_checks(video_id: str) -> None:
    threading.Thread(target=ytdlp_check, args=(video_id, "detect"), daemon=True).start()
    threading.Timer(RECHECK_AFTER, ytdlp_check, args=(video_id, "+15m")).start()


def main() -> None:
    channels = sys.argv[1:]
    OUT.mkdir(parents=True, exist_ok=True)
    # seen[(source, channel)] = các video đã thấy; vòng đầu chỉ làm mốc, không tính độ trễ.
    seen: dict[tuple[str, str], dict[str, str]] = {}  # video -> published
    checked: set[str] = set()
    log({"type": "start", "channels": channels, "api": api_key() is not None})
    while True:
        start = time.monotonic()
        key = api_key()
        for ch in channels:
            sources = [("rss", lambda c=ch: poll_rss(c))]
            if key:
                sources.append(("api", lambda c=ch, k=key: poll_api(c, k)))
            for source, poll in sources:
                try:
                    items, server_time, age = poll()
                except Exception as e:
                    msg = str(e).replace(key, "***") if key else str(e)
                    log({"type": "error", "source": source, "channel": ch, "error": msg[:300]})
                    continue
                prev = seen.get((source, ch))
                if prev is None:
                    seen[(source, ch)] = dict(items)
                    log({"type": "baseline", "source": source, "channel": ch, "n": len(items)})
                    continue
                for vid, pub in items.items():
                    if vid in prev:
                        continue
                    prev[vid] = pub
                    lat = (server_time - datetime.fromisoformat(pub)).total_seconds()
                    log(
                        {
                            "type": "new",
                            "source": source,
                            "channel": ch,
                            "video": vid,
                            "published": pub,
                            "first_seen": server_time.isoformat(),
                            "latency_s": round(lat),
                            "cache_age_s": age,
                        }
                    )
                    if vid not in checked:
                        checked.add(vid)
                        schedule_checks(vid)
                # Feed chập chờn: thiếu một video mới hơn video cũ nhất đang có trong feed.
                oldest = min(items.values(), default="")
                gone = [v for v, p in prev.items() if v not in items and p > oldest]
                if gone:
                    log({"type": "missing", "source": source, "channel": ch, "videos": gone})
        time.sleep(max(0, INTERVAL - (time.monotonic() - start)))


if __name__ == "__main__":
    main()
