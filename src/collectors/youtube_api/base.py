import os
import re
from contextlib import contextmanager
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build

from ..base import BaseCollector

_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_PLAYLIST_ID_RE = re.compile(r"^(PL|UU|LL|FL|OL|RD)[A-Za-z0-9_-]{10,}$")


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

    @staticmethod
    def _extract_channel_filter(target_url):
        """Trả về tham số lọc kênh cho channels.list từ URL, handle hoặc channel ID.

        Hỗ trợ /channel/UC..., /@handle, /user/<tên>, "@handle" và "UC...".
        URL dạng /c/<tên> không có tham số tương ứng trong API nên ném ValueError.
        """
        if _CHANNEL_ID_RE.match(target_url):
            return {"id": target_url}
        if target_url.startswith("@"):
            return {"forHandle": target_url}

        parsed = urlparse(target_url)
        host = (parsed.hostname or "").removeprefix("www.").removeprefix("m.")
        path = parsed.path.strip("/").split("/")
        if host.endswith("youtube.com"):
            if path[0] == "channel" and len(path) > 1 and _CHANNEL_ID_RE.match(path[1]):
                return {"id": path[1]}
            if path[0].startswith("@"):
                return {"forHandle": path[0]}
            if path[0] == "user" and len(path) > 1:
                return {"forUsername": path[1]}
        raise ValueError(f"Không nhận ra kênh từ URL: {target_url}")

    def _resolve_channel_id(self, client, target_url):
        """Đổi URL, handle hoặc tên người dùng thành channel ID.

        Chỉ gọi channels.list khi đầu vào chưa phải channel ID.
        Ném RuntimeError nếu kênh không tồn tại.
        """
        channel_filter = self._extract_channel_filter(target_url)
        if "id" in channel_filter:
            return channel_filter["id"]
        items = client.channels().list(part="id", **channel_filter).execute().get("items") or []
        if not items:
            raise RuntimeError(f"Không tìm thấy kênh từ URL: {target_url}")
        return items[0]["id"]

    @staticmethod
    def _extract_playlist_id(target_url):
        """Lấy playlist ID từ URL có tham số list= hoặc trả về nguyên giá trị nếu đã là ID."""
        if _PLAYLIST_ID_RE.match(target_url):
            return target_url
        playlist_id = parse_qs(urlparse(target_url).query).get("list", [None])[0]
        if not playlist_id or not _PLAYLIST_ID_RE.match(playlist_id):
            raise ValueError(f"Không nhận ra playlist ID từ URL: {target_url}")
        return playlist_id

    @staticmethod
    def _collect_pages(resource, request, max_items=None):
        """Duyệt các trang của request bằng list_next() và gộp items.

        max_items giới hạn tổng số phần tử trả về; None nghĩa là lấy hết.
        """
        items = []
        while request is not None:
            response = request.execute()
            items.extend(response.get("items", []))
            if max_items is not None and len(items) >= max_items:
                return items[:max_items]
            request = resource.list_next(request, response)
        return items
