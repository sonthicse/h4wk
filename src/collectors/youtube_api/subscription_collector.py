from typing import Any

from .base import YoutubeApiCollector


class SubscriptionCollector(YoutubeApiCollector):
    """Thu thập danh sách kênh mà một kênh đăng ký bằng subscriptions.list."""

    def collect(self, target_url: str, max_items: int | None = None) -> list[dict[str, Any]]:
        """Trả về danh sách resource subscription thô, duyệt hết các trang.

        Chỉ lấy được khi kênh công khai danh sách đăng ký; nếu không,
        API trả HttpError 403 (subscriptionForbidden) và lỗi được truyền lên.
        """
        with self._get_client() as client:
            channel_id = self._resolve_channel_id(client, target_url)
            resource = client.subscriptions()
            request = resource.list(
                part="snippet,contentDetails",
                channelId=channel_id,
                maxResults=50,
            )
            return self._collect_pages(resource, request, max_items)
