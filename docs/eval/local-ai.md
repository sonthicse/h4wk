# Đo kiểm AI cục bộ

## T55 — Jev trên `1RUJ_6eruwA`

Chạy trên bản sao dữ liệu (`r_01M7YK59N1E22J42T9ADPFDZAW`). Jev gửi thêm 16 mục: 1 tiêu đề, 0 mô tả (rỗng), 10 OCR, 1 visual, 4 thumbnail. Tổng cộng 26 mục, 0 lỗi, 19 nghi vấn Jev được giữ. Nghi vấn OCR tại `seg_0002` chứa dòng “CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ”.

## T52 — Ollama `qwen3-vl:4b` (thinking)

Chỉ dùng tuyến Ollama trong cấu hình sandbox. Ở mức 1024 token, khung còng tay có ba phản hồi liên tiếp với `finish_reason=length`, 1024 token đầu ra và `content` rỗng; phần `reasoning` dài 4.021–4.317 ký tự. Với 4096 token và timeout 300 giây, cả 9 phản hồi đều có JSON hợp lệ, không hết giới hạn. Thời gian trung bình 35,36 giây/ảnh.

| Lượt | Khung chữ `000015` | Khung còng `000025` | Khung thường `000032` |
| --- | --- | --- | --- |
| 1 | 41,26 s / 1.354 token / 4.845 ký tự suy luận | 78,49 s / 2.436 token / 8.370 ký tự | 22,82 s / 754 token / 2.848 ký tự |
| 2 | 33,36 s / 1.090 token / 3.956 ký tự suy luận | 72,79 s / 2.276 token / 7.954 ký tự | 13,46 s / 453 token / 1.580 ký tự |
| 3 | 17,98 s / 603 token / 1.854 ký tự suy luận | 20,55 s / 689 token / 2.181 ký tự | 17,49 s / 588 token / 2.315 ký tự |

API tương thích OpenAI trả tổng token đầu ra, không tách riêng số token suy luận; độ dài trường `reasoning` được ghi theo ký tự. Test T21 không đổi: đạt 0/3 lượt vì cả ba lượt đều bỏ sót dấu hiệu chữ buộc tội; ở lượt 3, “gông tay” cũng không khớp điều kiện kiểm “còng”/“handcuff”. Khung thường không sinh dấu hiệu ở cả ba lượt.

Chạy thử bổ sung ở mức 1024 token: trích hai khung từ clip tổng hợp `corner-text.mp4` bằng FFmpeg (một khung mỗi hai giây). Hai khung có cùng hash; cả hai lần gọi thành công, 31,20 và 39,88 giây (trung bình 35,54 giây). Hai mục trong `vision.json` đều ghi `provider: ollama`, `model: qwen3-vl:4b`.

Cùng hai khung với cấu hình cuối 4096 token: 2/2 thành công; 34,00 và 22,57 giây (trung bình 28,28 giây), tương ứng 1.176 và 760 token đầu ra theo thứ tự hoàn thành.
