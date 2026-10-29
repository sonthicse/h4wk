from typing import Any

from .base import YoutubeApiCollector
from .metadata_collector import DEFAULT_PARTS


class PopularVideoCollector(YoutubeApiCollector):
    """Thu thập video thịnh hành theo vùng bằng videos.list với chart=mostPopular."""

    def collect(
        self,
        region_code: str = "VN",
        video_category_id: str | None = None,
        max_items: int | None = None,
        parts=DEFAULT_PARTS,
    ) -> list[dict[str, Any]]:
        """Trả về danh sách resource video thô đang thịnh hành, duyệt hết các trang.

        region_code là mã quốc gia ISO 3166-1 alpha-2. video_category_id lọc
        theo thể loại (lấy mã từ VideoCategoryCollector); một số thể loại
        không có bảng xếp hạng và API trả HttpError 404.
        """
        params = {"chart": "mostPopular", "regionCode": region_code, "maxResults": 50}
        if video_category_id:
            params["videoCategoryId"] = video_category_id
        with self._get_client() as client:
            resource = client.videos()
            request = resource.list(part=",".join(parts), **params)
            return self._collect_pages(resource, request, max_items)
