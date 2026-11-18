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

Video vừa đăng: xem phần 2. Video `wwZNS9_ZdBs` của VTV24, khi được phát hiện khoảng 14 phút sau lúc đăng, đã có bản 1080p và phụ đề `vi-orig`.

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

Nhóm không có kênh thử nghiệm, nên không đăng video để đo. Thay vào đó, script [feed_latency.py](feed_latency.py) theo dõi 4 kênh tin tức đăng thường xuyên: HTV Tin Tức (`UCZYKmEA2iQOSbyKc6xj5Vfw`, khoảng 7 video/giờ), Báo Tuổi Trẻ (`UC47WI-kZXFf0H_f7pvaNCEQ`), VTV24 (`UCabsTV34JwALXKGMqHpvUiA`) và VnExpress (`UCpK5nl5llhUL4QKq03qan8g`). Script poll mỗi 30 giây. Độ trễ được tính bằng thời điểm video xuất hiện lần đầu trừ thời điểm đăng (`published`).

Phép đo chỉ chạy khoảng 15 phút, vào buổi tối khi các kênh gần như không đăng video mới, nên chỉ có **1 mẫu**: video `wwZNS9_ZdBs` của VTV24 xuất hiện trong RSS **599 giây (khoảng 10 phút)** sau lúc đăng.

Phát hiện chính đến từ header HTTP, không đến từ số mẫu:

- RSS của YouTube được cache với `Cache-Control: public, max-age=900`, tức tối đa 15 phút. Header `Age` quan sát được dao động từ 48 đến 863 giây.
- Có nhiều máy chủ cache, mỗi máy giữ một bản với độ cũ khác nhau. Ba request liên tiếp có thể nhận ba bản khác nhau. Vì vậy feed chập chờn: video `wwZNS9_ZdBs` xuất hiện ở một lần poll rồi biến mất ở lần poll sau.
- Đồng hồ máy chạy đúng (khớp header `Date` của Google tới từng giây), nên độ trễ không do lệch giờ trên WSL. Script lấy thời điểm nhận bằng `Date + Age`.

Do đó, độ trễ RSS gồm thời gian YouTube cập nhật feed cộng với tối đa 15 phút cache. Độ trễ này thường vượt 3 phút.

## Phần 3: độ trễ `playlistItems` của YouTube API

Phần này chưa có mẫu nào, vì trong thời gian chạy không kênh nào đăng video mới. Có hai quan sát:

- Phản hồi của `playlistItems` không có header `Cache-Control`, nên không bị cache ở CDN như RSS. Một lần chụp đồng thời cả 4 kênh cho thấy API và RSS có cùng video mới nhất, vì không có video nào mới đăng trong 40 phút trước đó.
- Mỗi lần gọi với `maxResults` tối đa 50 tốn 1 đơn vị quota. Poll 4 kênh mỗi 30 giây tốn khoảng 480 đơn vị/giờ, trong khi giới hạn là 10.000 đơn vị/ngày. Vì vậy chỉ nên gọi API khi bấm Check now, không nên poll liên tục.

Cần đo lại độ trễ thật của API khi làm T30 (nút Check now), bằng cách chạy lại `feed_latency.py` vào giờ các kênh đăng dày (sáng hoặc trưa).

## Kết luận

- yt-dlp chạy được trên máy này, sau khi cài Deno và `curl_cffi`, và chỉ lấy phụ đề tiếng Việt.
- **RSS trễ quá 3 phút**: cache 15 phút, cộng với mẫu đo được trễ 10 phút. Vì vậy **màn 3 dùng nút Check now lúc demo**. Nút này gọi `playlistItems` của YouTube API, vốn không bị cache CDN. Kiểm tra RSS định kỳ vẫn giữ để tiết kiệm quota.
- Watchlist phải chống trùng theo ID video và không coi việc một video biến mất khỏi feed là video bị xoá, vì RSS chập chờn giữa các máy chủ cache.
- Spike này dùng kênh tin tức của người khác vì nhóm không có kênh riêng. Nhóm quyết định giữ cách này cho màn 3 (SPEC đã cập nhật): màn 3 chỉ trình diễn phát hiện và tự xử lý video mới.
