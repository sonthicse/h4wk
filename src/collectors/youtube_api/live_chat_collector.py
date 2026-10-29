import time
from typing import Any

from .base import YoutubeApiCollector


class LiveChatCollector(YoutubeApiCollector):
    """Thu thập tin nhắn live chat của livestream đang phát bằng liveChatMessages.list.

    Live chat là luồng liên tục nên collector thăm dò theo pollingIntervalMillis
    do API trả về và dừng khi đủ max_messages, hết duration giây hoặc
    livestream kết thúc. Mỗi lần thăm dò tốn quota, nên cần đặt giới hạn hợp lý.
    """

    def collect(
        self,
        target_url: str,
        max_messages: int | None = 200,
        duration: float | None = 60,
    ) -> list[dict[str, Any]]:
        """Trả về danh sách resource liveChatMessage thô theo thứ tự nhận được.

        Phải có ít nhất một trong max_messages hoặc duration để tránh chạy mãi.
        Ném RuntimeError nếu video không phải livestream đang phát
        (không có activeLiveChatId).
        """
        if max_messages is None and duration is None:
            raise ValueError("Cần đặt max_messages hoặc duration")

        video_id = self._extract_video_id(target_url)
        messages = []
        deadline = None if duration is None else time.monotonic() + duration
        with self._get_client() as client:
            response = client.videos().list(part="liveStreamingDetails", id=video_id).execute()
            items = response.get("items") or []
            live_chat_id = items[0].get("liveStreamingDetails", {}).get("activeLiveChatId") if items else None
            if not live_chat_id:
                raise RuntimeError(f"Video không có live chat đang hoạt động: {target_url}")

            page_token = None
            while True:
                response = client.liveChatMessages().list(
                    part="snippet,authorDetails",
                    liveChatId=live_chat_id,
                    maxResults=2000,
                    pageToken=page_token,
                ).execute()
                messages.extend(response.get("items", []))
                if max_messages is not None and len(messages) >= max_messages:
                    return messages[:max_messages]
                if response.get("offlineAt") or not response.get("nextPageToken"):
                    return messages
                page_token = response["nextPageToken"]

                wait = response.get("pollingIntervalMillis", 5000) / 1000
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= wait:
                        return messages
                time.sleep(wait)
