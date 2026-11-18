# Spike T2: yt-dlp trên WSL và độ trễ RSS

Ngày chạy: 2026-11-18. Máy: WSL2 (Kali), mạng gia đình ở Việt Nam, không dùng cookies.

## Phần 1: yt-dlp

Script: [ytdlp_probe.py](ytdlp_probe.py).

```bash
uv run --no-project --with 'yt-dlp[default,curl-cffi]' \
    python docs/spikes/ytdlp_probe.py URL [URL ...]
```

### Kết quả

| Video | Độ dài | Đã đăng | Video | Phụ đề tiếng Việt | Comment | Dung lượng | Thời gian |
|---|---|---|---|---|---|---|---|
| `4_PbEIY_Pg4` (review phim) | 10:52 | ~4 năm | 720p AV1 + Opus | `vi-orig` (tự động) | 200 (chạm giới hạn của script) | 67.8 MB | 125 s* |
| `8ox5dG6sV5k` (Network Bắt Bệnh #06) | 8:19 | ~29 ngày | 720p AV1 + Opus | `vi-orig` (tự động) | 0 | 27.2 MB | 100 s* |
| `oAFNS8b7br0` (Network Bắt Bệnh #07) | 7:15 | ~10 ngày | 720p VP9 + Opus | `vi-orig` (tự động) | 0 | 21.1 MB | 13 s |

\* Lần chạy này mạng chập chờn (timeout, lỗi DNS), nên thời gian không đại diện. Lần chạy lại `oAFNS8b7br0` khi mạng ổn mất 13 s.

Cả 3 video đều có bản 720p kèm audio. Không video nào có phụ đề do người đăng tải lên, chỉ có phụ đề tự động. Phụ đề tự động giữ đúng dấu tiếng Việt và có mốc thời gian theo từng từ.

Chưa thử video vừa đăng vài phút. Việc này làm cùng phần 2, với video đăng lên kênh thử nghiệm.

### Lỗi gặp phải và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| Cảnh báo `No supported JavaScript runtime`. Không có JS runtime thì YouTube có thể thiếu định dạng | yt-dlp cần JS runtime để giải challenge của YouTube (EJS). Mặc định chỉ bật Deno | Cài Deno. Node cũng dùng được nếu thêm `--js-runtimes node` (đã thử: hết cảnh báo) |
| Cảnh báo `no impersonate target is available` | Thiếu thư viện giả lập trình duyệt | Cài `curl_cffi` (extra `yt-dlp[curl-cffi]`) |
| `HTTP Error 429: Too Many Requests` ngay ở bước tải phụ đề, cả 3 video | `subtitleslangs: ["all"]` kéo theo hơn 100 bản dịch máy của phụ đề tự động | Chỉ lấy phụ đề tiếng Việt: bản do người đăng tải lên (`vi*`) và bản tự động gốc `vi-orig`. Không lấy bản dịch máy |
| Timeout, `Network is unreachable`, lỗi DNS | Mạng của máy chập chờn trong lúc chạy | Chạy lại là được. Adapter cần xếp loại lỗi này vào `Transient` để thử lại |

Không gặp bot check, không bị đòi PO token, và không cần cookies.

### Phần mềm cần cài thêm cho yt-dlp

- `yt-dlp[default,curl-cffi]`, bản `2026.10.26`.
- Deno, bản 2.9.8 (cài bằng script chính thức vào `~/.deno`, rồi tạo symlink vào `~/.local/bin`).
- `ffmpeg` để ghép video và audio. Máy đã có sẵn bản 8.1.2.

### Điểm cần lưu ý cho adapter yt-dlp (T6)

- Với format `bv*[height<=720]+ba`, YouTube trả AV1 hoặc VP9 trong file `.mp4`. Bước tạo bản 480p (`ffmpeg`) đọc được các codec này. Nếu muốn file gốc phát được ở mọi trình duyệt thì có thể ưu tiên H.264 bằng `format_sort: ["vcodec:h264"]`. Cần quyết định lúc làm T6.
- Khi đặt `max_comments`, yt-dlp ghi `comment_count` bằng số comment đã lấy, nên mất tổng số comment thật. Muốn có tổng thật thì phải lấy ở bước đọc metadata (chưa bật `getcomments`), hoặc từ YouTube API.
- Adapter chỉ lấy phụ đề tiếng Việt, giống spike này. SPEC đã được cập nhật (phần 13).

## Phần 2: độ trễ RSS

Chưa làm. Cần kênh thử nghiệm để đăng 3 video.

## Phần 3: độ trễ `playlistItems` của YouTube API

Chưa làm. Cần YouTube API key.

## Kết luận

Chưa có kết luận. Phần 1 cho thấy yt-dlp chạy được trên máy này, sau khi cài Deno và `curl_cffi` và chỉ lấy phụ đề tiếng Việt.
