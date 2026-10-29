from typing import Any

from .base import YoutubeApiCollector


class ChannelSectionCollector(YoutubeApiCollector):
    """Thu thập các section hiển thị trên trang kênh bằng channelSections.list."""

    def collect(self, target_url: str) -> list[dict[str, Any]]:
        """Trả về danh sách resource channelSection thô của kênh.

        channelSections.list không phân trang nên chỉ gọi một lần.
        """
        with self._get_client() as client:
            channel_id = self._resolve_channel_id(client, target_url)
            response = client.channelSections().list(
                part="snippet,contentDetails",
                channelId=channel_id,
            ).execute()
        return response.get("items", [])
