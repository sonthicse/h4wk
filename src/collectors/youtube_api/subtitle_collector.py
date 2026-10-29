from typing import Any

from .base import YoutubeApiCollector


class SubtitleCollector(YoutubeApiCollector):
    """Thu thập phụ đề của video bằng captions.list và captions.download.

    captions.list dùng được với API key, còn captions.download bắt buộc
    credentials OAuth của tài khoản có quyền sửa video.
    """

    def list_tracks(self, target_url: str) -> list[dict[str, Any]]:
        """Trả về danh sách resource caption thô của video."""
        video_id = self._extract_video_id(target_url)
        with self._get_client() as client:
            response = client.captions().list(part="snippet", videoId=video_id).execute()
        return response.get("items", [])

    def collect(self, target_url: str, lang: str, tfmt: str = "srt") -> dict[str, Any]:
        """Trả về track phụ đề và nội dung tải về theo định dạng tfmt.

        Ưu tiên track thủ công (trackKind standard); nếu không có thì lấy
        track tự động (ASR). Không có track ngôn ngữ lang thì ném ValueError.
        Không có credentials OAuth thì ném PermissionError trước khi gọi download.
        Kết quả gồm "track" (resource caption thô) và "content" (chuỗi phụ đề).
        """
        tracks = [t for t in self.list_tracks(target_url) if t["snippet"].get("language") == lang]
        if not tracks:
            raise ValueError(f"Không tìm thấy phụ đề ngôn ngữ '{lang}' (cả thủ công và tự động)")
        track = next((t for t in tracks if t["snippet"].get("trackKind") != "asr"), tracks[0])

        if self._opts.get("credentials") is None:
            raise PermissionError("captions.download cần credentials OAuth của chủ video, API key không đủ quyền")

        with self._get_client() as client:
            raw = client.captions().download(id=track["id"], tfmt=tfmt).execute()
        content = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        return {"track": track, "content": content}
