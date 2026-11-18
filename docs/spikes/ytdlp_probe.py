"""Spike T2 phần 1: thử yt-dlp lấy metadata, phụ đề tiếng Việt, comment và video 720p.

Chạy từ gốc repo:
    uv run --no-project --with 'yt-dlp[default,curl-cffi]' \\
        python docs/spikes/ytdlp_probe.py URL [URL ...]

Kết quả ghi vào .tmp/spike-ytdlp/<video_id>/ (đã .gitignore) và in tóm tắt từng video.
Script dùng một lần cho spike, không phải code của sản phẩm.
"""

import json
import sys
import time
from pathlib import Path

import yt_dlp

OUT = Path(".tmp/spike-ytdlp")
MAX_COMMENTS = 200  # giới hạn để spike chạy nhanh


def probe(url: str) -> dict:
    opts = {
        "outtmpl": str(OUT / "%(id)s" / "%(id)s.%(ext)s"),
        "format": "bv*[height<=720]+ba/b[height<=720]",
        "merge_output_format": "mp4",
        "writeinfojson": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "getcomments": True,
        "extractor_args": {"youtube": {"max_comments": [str(MAX_COMMENTS)]}},
        "quiet": True,
        "noprogress": True,
        "no_warnings": False,
    }
    t0 = time.monotonic()
    result: dict = {"url": url, "yt_dlp": yt_dlp.version.__version__}
    try:
        # Bước 1: chỉ đọc metadata để biết có phụ đề nào.
        with yt_dlp.YoutubeDL({**opts, "getcomments": False}) as ydl:
            pre = ydl.extract_info(url, download=False)
        # Chỉ lấy phụ đề tiếng Việt: bản người đăng tải lên (vi, vi-VN...) và bản tự động gốc.
        # Không lấy bản dịch máy: lấy "all" kéo theo hơn 100 ngôn ngữ và bị HTTP 429.
        manual_vi = [k for k in (pre.get("subtitles") or {}) if k.startswith("vi")]
        auto_vi = [k for k in (pre.get("automatic_captions") or {}) if k == "vi-orig"]
        langs = sorted(manual_vi) + auto_vi
        result["sub_langs_requested"] = langs
        # Bước 2: tải thật.
        with yt_dlp.YoutubeDL({**opts, "subtitleslangs": langs}) as ydl:
            info = ydl.extract_info(url, download=True)
        vid_dir = OUT / info["id"]
        result.update(
            ok=True,
            id=info["id"],
            title=info.get("title"),
            age_seconds=int(time.time()) - (info.get("timestamp") or 0),
            height=info.get("height"),
            manual_subs=sorted(info.get("subtitles") or {}),
            auto_subs_vi="vi" in (info.get("automatic_captions") or {}),
            comments=len(info.get("comments") or []),
            comment_count=info.get("comment_count"),
            files=sorted(p.name for p in vid_dir.iterdir()),
            size_mb=round(sum(p.stat().st_size for p in vid_dir.iterdir()) / 1e6, 1),
        )
    except Exception as e:  # spike: ghi lại mọi lỗi để phân loại
        result.update(ok=False, error_type=type(e).__name__, error=str(e)[:500])
    result["seconds"] = round(time.monotonic() - t0, 1)
    return result


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results = [probe(u) for u in sys.argv[1:]]
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
