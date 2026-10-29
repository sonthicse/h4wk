from typing import Any

from .base import YtDlpCollector


class MetadataCollector(YtDlpCollector):
    """Thu thập toàn bộ thông tin mặc định từ yt-dlp, không tải media."""

    def collect(self, target_url: str) -> dict[str, Any]:
        """Trả về kết quả thô của một lần gọi extract_info(), không lọc trường.

        Không bật thêm việc thu thập bình luận hay tải phụ đề mặc định.
        Các trường có sẵn phụ thuộc URL, extractor và custom_opts.
        Kết quả có thể chứa đối tượng không serialize trực tiếp sang JSON.
        Lỗi từ yt-dlp được truyền lên bên gọi; nếu không có kết quả,
        ném RuntimeError thay vì trả về dữ liệu rỗng.
        """
        with self._get_ydl_instance() as ydl:
            info = ydl.extract_info(target_url, download=False)
            if info is None:
                raise RuntimeError(f"Không thu thập được metadata từ URL: {target_url}")
            return info

# import json

# collector = MetadataCollector()

# target_url = "https://www.youtube.com/watch?v=hZVH-y1atWw"
# info = collector.collect(target_url)
# output_file = "metadata.json"
# with open(output_file, "w", encoding="utf-8") as f:
#     json.dump(info, f, ensure_ascii=False, indent=4, default=str)
