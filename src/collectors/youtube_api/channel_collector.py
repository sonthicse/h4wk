from typing import Any

from .base import YoutubeApiCollector

# auditDetails và contentOwnerDetails chỉ dành cho chủ kênh hoặc đối tác
# nội dung nên không đưa vào mặc định.
DEFAULT_PARTS = (
    "snippet",
    "contentDetails",
    "statistics",
    "status",
    "topicDetails",
    "brandingSettings",
    "localizations",
)


class ChannelCollector(YoutubeApiCollector):
    """Thu thập thông tin kênh bằng channels.list, không lọc trường."""

    def collect(self, target_url: str, parts=DEFAULT_PARTS) -> dict[str, Any]:
        """Trả về resource channel thô từ một lần gọi channels.list.

        target_url có thể là URL kênh, "@handle" hoặc channel ID.
        Ném RuntimeError nếu kênh không tồn tại.
        """
        channel_filter = self._extract_channel_filter(target_url)
        with self._get_client() as client:
            response = client.channels().list(part=",".join(parts), **channel_filter).execute()
        items = response.get("items") or []
        if not items:
            raise RuntimeError(f"Không thu thập được thông tin kênh từ URL: {target_url}")
        return items[0]
