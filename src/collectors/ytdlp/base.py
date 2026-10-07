from contextlib import contextmanager

import yt_dlp

from ..base import BaseCollector


class YtDlpCollector(BaseCollector):
    """Lớp cơ sở cho collector dùng yt-dlp, không quy định schema kết quả.

    Lớp con phải triển khai collect() và dùng _get_ydl_instance() trong
    khối with để tài nguyên được đóng kể cả khi có lỗi.
    """

    def __init__(self, custom_opts=None):
        self._opts = {
            "quiet": True,
            "no_warnings": False,
            "skip_download": True,
            "js_runtimes": {"node": {}},
        }
        if custom_opts:
            self._opts.update(custom_opts)

    @contextmanager
    def _get_ydl_instance(self, extra_opts=None):
        """Tạo context manager cho YoutubeDL với cấu hình riêng từng lần gọi.

        Thứ tự ưu tiên: extra_opts > custom_opts > cấu hình mặc định.
        Cấu hình được sao chép nông; giá trị lồng nhau không được sao chép.
        Lỗi từ yt-dlp được truyền lên bên gọi.
        """
        opts = self._opts.copy()
        if extra_opts:
            opts.update(extra_opts)
        with yt_dlp.YoutubeDL(opts) as ydl:
            yield ydl
