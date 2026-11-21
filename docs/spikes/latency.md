# Độ trễ giao diện

## Dashboard (T35)

Đo ngày 20/11/2026 bằng playwright (Chromium) trên bản build production (`npm run build`, `vite preview` cổng 5182, proxy `/api` sang backend cổng 8010).

- Máy: Intel Core i7-12700 (20 luồng), backend và trình duyệt cùng máy.
- Dữ liệu: bản sao `data/` thật, sau `h4wk reindex`: 77 video, 231 nghi vấn, 7 quyết định rà soát.
- Cách đo: đăng nhập, rồi `goto /` năm lần (lần 1 lạnh, bốn lần sau ấm). "Số liệu hiện" là thời điểm (tính từ lúc bắt đầu điều hướng) khối thống kê hiện số "Videos collected". `load` là `loadEventEnd` của navigation timing. Thời gian API là `responseEnd − startTime` của request tương ứng.

| Lần | load (ms) | Số liệu hiện (ms) | `/api/dashboard` (ms) | `/api/events` (ms) |
|---|---|---|---|---|
| 1 (lạnh) | 17 | 288 | 45 | 6 |
| 2 | 16 | 318 | 69 | 4 |
| 3 | 57 | 339 | 46 | 5 |
| 4 | 17 | 283 | 45 | 4 |
| 5 | 53 | 329 | 45 | 7 |

Kết quả: số liệu hiện xong trong 283–339 ms cả 5 lần, đạt ngưỡng dưới 1000 ms. Số đo là cận trên vì vòng chờ của script cách nhau 10 ms.

## Watchlist tự thu video mới (T30, màn 3)

Đo trên app `main` (5173/8000), 21/11/2026, bằng dữ liệu watchlist thật. Kênh VTV24 (`@vtv24`, mục `w_005`) đã nằm trong watchlist từ 20/11 ở mức `metadata`, nên bấm "Add to watchlist" lần nữa không tạo mục mới; số đo lấy từ lịch sử poll tự động của kênh này (27 sự kiện `new_video`, 37 job), không phải từ một kênh thêm mới trong phiên này.

| Mốc | Kết quả |
|---|---|
| 10 job ban đầu (13:40:04) | cả 10 `done`, cập nhật cuối 14:03:34 |
| Video mới → `new_video` | video đăng 16:20:27, sự kiện 16:34:38 (trễ ~14 phút, khớp RSS YouTube cache tới 15 phút) |
| `new_video` → `job_done` (mức `metadata`) | 2–17 giây cho cả 27 video, 0 job lỗi |
| Check now ngay sau poll | trả `new_videos: []`, số job của kênh giữ nguyên 37 → 37, không tạo job trùng |

Ảnh Watchlist: `docs/spikes/img/t30-watchlist.png`.

Hạn chế: không chạy riêng một kênh mới ở mức `text`; ảnh dòng sự kiện chưa chụp. Kênh VTV24 vẫn đang bật (đang dùng cho demo), không tắt.
