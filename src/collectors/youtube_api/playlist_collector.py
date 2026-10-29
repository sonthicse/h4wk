from typing import Any

from .base import YoutubeApiCollector

DEFAULT_PARTS = ("snippet", "contentDetails", "status", "player", "localizations")


class PlaylistCollector(YoutubeApiCollector):
    """Thu thập thông tin playlist bằng playlists.list, không lọc trường."""

    def collect(self, target_url: str, parts=DEFAULT_PARTS) -> dict[str, Any]:
        """Trả về resource playlist thô từ URL có tham số list= hoặc playlist ID.

        Ném RuntimeError nếu playlist không tồn tại hoặc không công khai.
        """
        playlist_id = self._extract_playlist_id(target_url)
        with self._get_client() as client:
            response = client.playlists().list(part=",".join(parts), id=playlist_id).execute()
        items = response.get("items") or []
        if not items:
            raise RuntimeError(f"Không thu thập được thông tin playlist từ URL: {target_url}")
        return items[0]
