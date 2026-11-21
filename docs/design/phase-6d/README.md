# Bản phác giao diện Phase 6d

Thi duyệt ngày 2026-11-21. Đây là nguồn chuẩn cho agent: đọc các file ở đây, không cần mở canvas gốc. Mỗi file `.dc.html` là một màn, viết bằng HTML với style inline; `{{…}}`, `<sc-for>`, `<sc-if>`, `<dc-import>` là cú pháp của canvas, không phải React.

Cách dùng: làm theo bố cục, nội dung, nhãn và định dạng trong bản phác, nhưng dựng bằng component có sẵn trong `web/src/components/ui` (shadcn) và màu theo `web/src/index.css`, không chép style inline. Chuyển động (chọn keyframe, đổi dòng đang phát, hiện/ẩn khung bao, đổi tab, số đếm) dùng animate-ui (`@animate-ui/react`, registry `@animate-ui` trong `web/components.json`, icon ở `web/src/components/animate-ui/icons`), như các màn đã có; không thêm thư viện animation khác. Chỗ ghi `[n]`, `[tokens]`, `[used]`, `[limit]`, `[left]` là số lấy từ API; ô xám là ảnh hoặc video.

| File | Màn | Task |
|---|---|---|
| `Dashboard.dc.html` | Dashboard | T66 |
| `Collect.dc.html` | Collect | T63 |
| `Videos.dc.html` | Videos | T66 |
| `Findings.dc.html` | Findings | không đổi |
| `Review.dc.html` | Review queue | không đổi |
| `FindingReview.dc.html` | Review per finding | không đổi |
| `Video.dc.html` | Video detail | T63 |
| `Watchlist.dc.html` | Watchlist | không đổi |
| `Entities.dc.html` | Entities | T66 |
| `Sources.dc.html` | Settings → Sources | không đổi |
| `SettingsJev.dc.html` | Settings → Jev | T62 |
| `Login.dc.html` | Login | T66 |
| `Sidebar.dc.html` | Thanh bên dùng chung | không đổi |

Màn "không đổi" vẽ lại để thấy cả app; không sửa theo bản phác trừ khi task ghi rõ.
