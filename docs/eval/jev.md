# Đánh giá Jev (T47)

- Recall của LLM cũ trên bộ 124 dòng: chưa đo, chờ quota Gemini.
- Precision của Jev trên 50 mẫu mù đã bị đánh dấu ở ngưỡng 0,5 và không có dấu hiệu khớp tên: **9/50 (18%)**; lời nói **1/12**, bình luận **8/38**. Nhãn do agent reviewer gán, không phải người. File mù không có đối tượng do Jev chọn, nên reviewer đánh giá theo văn bản và ngữ cảnh, xét nội dung nhắm vào Đảng, Nhà nước, chế độ hoặc lãnh đạo.

## Chạy API thật trên bản sao dữ liệu

| Video | Request | Nghi vấn Jev | Lỗi request |
| --- | ---: | ---: | ---: |
| `3KxAJpOuHHA` | 383 | 187 | 0 |
| `7aqvUHMVABQ` | 43 | 7 | 0 |
| `8VB-P9Wk7v4` | 201 | 111 | 0 |
| `EWbg9jbgzpU` | 389 | 196 | 0 |
| `UB1bh7cpFiA` | 434 | 235 | 0 |
| `WzNLx7x75Vo` | 169 | 77 | 0 |
| `hWk0BwVBgZs` | 313 | 135 | 0 |
| `mETeePPB_3c` | 334 | 124 | 0 |
| **Tổng** | **2266** | **1072** | **0** |

Các phản hồi có lựa chọn đối tượng, lựa chọn và xác suất danh mục, và điểm mức độ ở đúng trường. Tính lại quy tắc tổng xác suất ≥ 0,5 và đối tượng khác `none` trên các phản hồi thô cho kết quả trùng khớp với cờ `kept` ở mọi request. Tỷ lệ giữ khoảng 47% trên 8 video này không phải là precision. Kết quả chấm mù cho thấy nhiều báo động sai trên nhóm mẫu không khớp tên; không suy rộng 18% ra toàn bộ nghi vấn và chưa thể so sánh với LLM cũ.
