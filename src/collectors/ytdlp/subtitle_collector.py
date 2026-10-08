import json
from typing import Any

from yt_dlp.networking import Request

from .base import YtDlpCollector


class SubtitleCollector(YtDlpCollector):
    """Thu thập subtitle từ URL bằng yt-dlp, không tải media."""

    def collect(self, target_url: str, lang: str) -> dict[str, Any]:
        """Trả về phụ đề dạng JSON3 nguyên bản của một lần gọi extract_info().

        Ưu tiên phụ đề thủ công của chủ kênh; nếu không có thì lấy phụ đề
        tự động của YouTube. Nếu cả hai đều không có (hoặc không có định
        dạng json3), ném ValueError. Không tải video, không ghi file.
        """
        with self._get_ydl_instance(extra_opts={"noplaylist": True}) as ydl:
            try:
                info = ydl.extract_info(target_url, download=False)
            except Exception as e:
                if "429" in str(e):
                    raise RuntimeError("Bị YouTube chặn (429 Too Many Requests)") from e
                raise
            if info is None:
                raise RuntimeError(f"Không thu thập được dữ liệu từ URL: {target_url}")

            manual_subs = info.get("subtitles") or {}
            auto_subs = info.get("automatic_captions") or {}

            if lang in manual_subs:
                formats = manual_subs[lang]
            elif lang in auto_subs:
                formats = auto_subs[lang]
            else:
                raise ValueError(
                    f"Không tìm thấy phụ đề ngôn ngữ '{lang}' (cả thủ công và tự động)"
                )

            subtitle = next(
                (item for item in formats if item.get("ext") == "json3"),
                None,
            )
            if subtitle is None:
                raise ValueError(f"Phụ đề '{lang}' không hỗ trợ định dạng json3")

            try:
                with ydl.urlopen(Request(subtitle["url"])) as response:
                    raw = response.read()
            except Exception as e:
                if "429" in str(e):
                    raise RuntimeError("Bị YouTube chặn (429 Too Many Requests)") from e
                raise

            return json.loads(raw.decode("utf-8"))


collector = SubtitleCollector()

target_url = "https://www.youtube.com/watch?v=4ycKrWTvzNY"
lang = "vi"

try:
    data = collector.collect(target_url, lang="vi")
    print(f"===== NỘI DUNG PHỤ ĐỀ ({lang}) =====")
    for event in data.get("events", []):
        text = "".join(seg.get("utf8", "") for seg in event.get("segs", [])).strip()
        if text:
            print(text)
except (RuntimeError, ValueError) as e:
    print(e)
