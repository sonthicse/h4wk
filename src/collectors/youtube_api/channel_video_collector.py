from typing import Any

from .base import YoutubeApiCollector


class ChannelVideoCollector(YoutubeApiCollector):
    """Thu thập danh sách video đã đăng của kênh qua playlist uploads."""

    def collect(self, target_url: str, max_items: int | None = None) -> list[dict[str, Any]]:
        """Trả về danh sách resource playlistItem thô của playlist uploads.

        Mỗi phần tử chỉ có snippet và contentDetails của mục trong playlist;
        dùng MetadataCollector với contentDetails.videoId để lấy đủ thông tin video.
        Ném RuntimeError nếu kênh không tồn tại.
        """
        channel_filter = self._extract_channel_filter(target_url)
        with self._get_client() as client:
            response = client.channels().list(part="contentDetails", **channel_filter).execute()
            items = response.get("items") or []
            if not items:
                raise RuntimeError(f"Không tìm thấy kênh từ URL: {target_url}")
            uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

            resource = client.playlistItems()
            request = resource.list(
                part="snippet,contentDetails,status",
                playlistId=uploads_id,
                maxResults=50,
            )
            return self._collect_pages(resource, request, max_items)
