from typing import Any

from .base import YoutubeApiCollector


class PlaylistItemCollector(YoutubeApiCollector):
    """Thu thập các mục trong playlist bằng playlistItems.list."""

    def collect(self, target_url: str, max_items: int | None = None) -> list[dict[str, Any]]:
        """Trả về danh sách resource playlistItem thô, duyệt hết các trang.

        Mỗi phần tử chỉ có thông tin của mục trong playlist; dùng
        MetadataCollector với contentDetails.videoId để lấy đủ thông tin video.
        """
        playlist_id = self._extract_playlist_id(target_url)
        with self._get_client() as client:
            resource = client.playlistItems()
            request = resource.list(
                part="snippet,contentDetails,status",
                playlistId=playlist_id,
                maxResults=50,
            )
            return self._collect_pages(resource, request, max_items)
