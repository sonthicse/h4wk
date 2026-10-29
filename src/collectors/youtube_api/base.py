import os
import re
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build

from ..base import BaseCollector

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YoutubeApiCollector(BaseCollector):
    """Lớp cơ sở cho collector dùng YouTube Data API v3, không quy định schema kết quả.

    Lớp con phải triển khai collect() và dùng _get_client() trong khối with
    để tài nguyên được đóng kể cả khi có lỗi.
    """

    def __init__(self, api_key=None, credentials=None, custom_opts=None):
        """Khởi tạo collector với API key hoặc credentials OAuth.

        Nếu không truyền cả hai, đọc API key từ biến môi trường YOUTUBE_API_KEY.
        custom_opts được truyền thẳng vào googleapiclient.discovery.build().
        """
        api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not api_key and credentials is None:
            raise ValueError("Cần api_key, credentials hoặc biến môi trường YOUTUBE_API_KEY")
        self._opts = {
            "developerKey": api_key,
            "credentials": credentials,
            "cache_discovery": False,
        }
        if custom_opts:
            self._opts.update(custom_opts)

    @contextmanager
    def _get_client(self, extra_opts=None):
        """Tạo context manager cho client YouTube Data API v3.

        Thứ tự ưu tiên: extra_opts > custom_opts > cấu hình mặc định.
        Lỗi từ API (HttpError) được truyền lên bên gọi.
        """
        opts = self._opts.copy()
        if extra_opts:
            opts.update(extra_opts)
        client = build("youtube", "v3", **opts)
        try:
            yield client
        finally:
            client.close()

    @staticmethod
    def _extract_video_id(target_url):
        """Lấy video ID từ URL YouTube hoặc trả về nguyên giá trị nếu đã là ID.

        Hỗ trợ dạng watch?v=, youtu.be/, /shorts/, /embed/, /live/ và /v/.
        Ném ValueError nếu không nhận ra video ID.
        """
        if _VIDEO_ID_RE.match(target_url):
            return target_url

        parsed = urlparse(target_url)
        host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.")
        path = parsed.path.strip("/").split("/")

        video_id = None
        if host == "youtu.be":
            video_id = path[0]
        elif host.endswith("youtube.com") or host == "youtube-nocookie.com":
            if path[0] == "watch":
                video_id = parse_qs(parsed.query).get("v", [None])[0]
            elif path[0] in ("shorts", "embed", "live", "v") and len(path) > 1:
                video_id = path[1]

        if not video_id or not _VIDEO_ID_RE.match(video_id):
            raise ValueError(f"Không nhận ra video ID từ URL: {target_url}")
        return video_id
