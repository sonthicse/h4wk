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
