from typing import Any

from .base import YoutubeApiCollector

DEFAULT_PARTS = (
    "snippet",
    "contentDetails",
    "statistics",
    "status",
    "topicDetails",
    "player",
    "recordingDetails",
    "liveStreamingDetails",
    "localizations",
    "paidProductPlacementDetails",
)


class MetadataCollector(YoutubeApiCollector):
    """Thu thập metadata của video bằng videos.list, không lọc trường."""

    def collect(self, target_url: str, parts=DEFAULT_PARTS) -> dict[str, Any]:
        """Trả về resource video thô từ một lần gọi videos.list.

        Các trường có sẵn phụ thuộc video và danh sách parts.
        Lỗi từ API được truyền lên bên gọi; nếu video không tồn tại
        hoặc không công khai, ném RuntimeError thay vì trả về dữ liệu rỗng.
        """
        video_id = self._extract_video_id(target_url)
        with self._get_client() as client:
            response = client.videos().list(part=",".join(parts), id=video_id).execute()
        items = response.get("items") or []
        if not items:
            raise RuntimeError(f"Không thu thập được metadata từ URL: {target_url}")
        return items[0]
