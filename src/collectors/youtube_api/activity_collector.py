from typing import Any

from .base import YoutubeApiCollector


class ActivityCollector(YoutubeApiCollector):
    """Thu thập hoạt động công khai của kênh (đăng video, thêm vào playlist...)."""

    def collect(self, target_url: str, max_items: int | None = None) -> list[dict[str, Any]]:
        """Trả về danh sách resource activity thô của kênh, duyệt hết các trang."""
        with self._get_client() as client:
            channel_id = self._resolve_channel_id(client, target_url)
            resource = client.activities()
            request = resource.list(
                part="snippet,contentDetails",
                channelId=channel_id,
                maxResults=50,
            )
            return self._collect_pages(resource, request, max_items)
