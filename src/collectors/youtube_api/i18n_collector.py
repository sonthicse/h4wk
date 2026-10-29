from typing import Any

from .base import YoutubeApiCollector


class LanguageCollector(YoutubeApiCollector):
    """Thu thập danh sách ngôn ngữ giao diện YouTube hỗ trợ bằng i18nLanguages.list."""

    def collect(self, hl: str = "vi") -> list[dict[str, Any]]:
        """Trả về danh sách resource i18nLanguage thô; hl là ngôn ngữ của tên hiển thị."""
        with self._get_client() as client:
            response = client.i18nLanguages().list(part="snippet", hl=hl).execute()
        return response.get("items", [])


class RegionCollector(YoutubeApiCollector):
    """Thu thập danh sách vùng nội dung YouTube hỗ trợ bằng i18nRegions.list."""

    def collect(self, hl: str = "vi") -> list[dict[str, Any]]:
        """Trả về danh sách resource i18nRegion thô; hl là ngôn ngữ của tên hiển thị."""
        with self._get_client() as client:
            response = client.i18nRegions().list(part="snippet", hl=hl).execute()
        return response.get("items", [])
