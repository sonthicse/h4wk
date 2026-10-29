from typing import Any

from .base import YoutubeApiCollector
from .playlist_collector import DEFAULT_PARTS


class ChannelPlaylistCollector(YoutubeApiCollector):
    """Thu thập các playlist công khai của kênh bằng playlists.list."""

    def collect(
        self,
        target_url: str,
        max_items: int | None = None,
        parts=DEFAULT_PARTS,
    ) -> list[dict[str, Any]]:
        """Trả về danh sách resource playlist thô của kênh, duyệt hết các trang."""
        with self._get_client() as client:
            channel_id = self._resolve_channel_id(client, target_url)
            resource = client.playlists()
            request = resource.list(part=",".join(parts), channelId=channel_id, maxResults=50)
            return self._collect_pages(resource, request, max_items)
