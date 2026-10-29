from typing import Any

from .base import YoutubeApiCollector


class SearchCollector(YoutubeApiCollector):
    """Thu thập kết quả tìm kiếm bằng search.list.

    Mỗi trang search.list tốn 100 đơn vị quota (gấp 100 lần các lệnh list
    khác), nên max_items mặc định chỉ lấy một trang 50 kết quả.
    """

    def collect(self, query: str, max_items: int | None = 50, **search_params) -> list[dict[str, Any]]:
        """Trả về danh sách resource searchResult thô cho từ khoá query.

        search_params được truyền thẳng vào search.list, ví dụ type="video",
        order="date", regionCode="VN", publishedAfter="2026-01-01T00:00:00Z".
        Kết quả chỉ có snippet; dùng MetadataCollector để lấy đủ thông tin video.
        """
        with self._get_client() as client:
            resource = client.search()
            request = resource.list(part="snippet", q=query, maxResults=50, **search_params)
            return self._collect_pages(resource, request, max_items)
