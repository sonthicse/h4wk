from typing import Any

from .base import YoutubeApiCollector


class CommentCollector(YoutubeApiCollector):
    """Thu thập bình luận của video bằng commentThreads.list và comments.list."""

    def collect(
        self,
        target_url: str,
        max_comments: int | None = None,
        fetch_all_replies: bool = True,
    ) -> list[dict[str, Any]]:
        """Trả về danh sách resource commentThread thô, duyệt hết các trang.

        commentThreads.list chỉ kèm tối đa 5 phản hồi mỗi thread; khi
        fetch_all_replies bật, phản hồi còn thiếu được lấy qua comments.list
        và ghi đè vào replies.comments. max_comments giới hạn số thread.
        Lỗi từ API (ví dụ commentsDisabled) được truyền lên bên gọi.
        """
        video_id = self._extract_video_id(target_url)
        with self._get_client() as client:
            resource = client.commentThreads()
            request = resource.list(part="snippet,replies", videoId=video_id, maxResults=100)
            threads = self._collect_pages(resource, request, max_comments)

            if fetch_all_replies:
                for thread in threads:
                    total = thread["snippet"].get("totalReplyCount", 0)
                    replies = thread.get("replies", {}).get("comments", [])
                    if total > len(replies):
                        thread["replies"] = {"comments": self._collect_replies(client, thread["id"])}
        return threads

    def _collect_replies(self, client, parent_id):
        """Lấy toàn bộ phản hồi của một bình luận gốc qua comments.list."""
        resource = client.comments()
        request = resource.list(part="snippet", parentId=parent_id, maxResults=100)
        return self._collect_pages(resource, request)
