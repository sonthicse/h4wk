from typing import Any

from .base import YoutubeApiCollector


class VideoCategoryCollector(YoutubeApiCollector):
    """Thu thập danh sách thể loại video theo vùng bằng videoCategories.list."""

    def collect(self, region_code: str = "VN", hl: str = "vi") -> list[dict[str, Any]]:
        """Trả về danh sách resource videoCategory thô của vùng region_code.

        hl quy định ngôn ngữ của tên thể loại trong snippet.title.
        """
        with self._get_client() as client:
            response = client.videoCategories().list(
                part="snippet",
                regionCode=region_code,
                hl=hl,
            ).execute()
        return response.get("items", [])
