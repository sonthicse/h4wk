from typing import Any

from .base import YtDlpCollector


class CommentCollector(YtDlpCollector):
    """Thu thập bình luận từ URL bằng yt-dlp, không tải media."""

    def collect(self, target_url: str) -> list[dict[str, Any]]:
        """Trả về danh sách bình luận từ một lần gọi extract_info().

        Bật tuỳ chọn getcomments để yt-dlp thu thập comment.
        Mỗi phần tử là dict thô của yt-dlp (author, text, timestamp, ...).
        Lỗi từ yt-dlp được truyền lên bên gọi; nếu không thu thập được
        thông tin hoặc không có comment, ném RuntimeError.
        """
        with self._get_ydl_instance(extra_opts={"getcomments": True}) as ydl:
            info = ydl.extract_info(target_url, download=False)
            if info is None:
                raise RuntimeError(f"Không thu thập được dữ liệu từ URL: {target_url}")
            comments = info.get("comments")
            if comments is None:
                raise RuntimeError(f"Không lấy được comment từ URL: {target_url}")
            return comments



collector = CommentCollector()

target_url = "https://www.youtube.com/watch?v=hZVH-y1atWw"
comments = collector.collect(target_url)

#import json 
#output_file = "comments.json"
#with open(output_file, "w", encoding="utf-8") as f:
    #json.dump(comments, f, ensure_ascii=False, indent=4, default=str)
#print(f"Đã thu thập {len(comments)} comment từ: {target_url}")
#print(f"Đã lưu kết quả vào: {output_file}")