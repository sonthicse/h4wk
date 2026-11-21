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


## So sánh theo ngưỡng

Tính lại trên phản hồi đã lưu, không gửi thêm request. Hai cột dùng hai tập mẫu khác nhau: precision tính trên phần còn giữ của 50 mẫu mù không khớp tên; recall tính trên 82 bình luận vi phạm có nhắc tên trong `trial.csv`.

| Ngưỡng | Precision trên mẫu mù | Recall Jev trên bình luận có nhắc tên |
| ---: | ---: | ---: |
| 0,5 | 9/50 (18,0%) | 81/82 (98,8%) |
| 0,7 | 8/33 (24,2%) | 70/82 (85,4%) |
| 0,9 | 6/14 (42,9%) | 57/82 (69,5%) |

T47 giữ ngưỡng 0,5 theo SPEC 10.6. Nâng ngưỡng loại bớt báo động sai nhưng cũng bỏ sót thêm bình luận vi phạm trong tập thử nghiệm; ngay ở 0,9 vẫn còn 8/14 mẫu báo động sai. Bảng này không đo recall của LLM cũ.

## Chạy thật với ảnh (T59)

Bản sao capture `20261120T132008` của `1RUJ_6eruwA` (sau T58), `max_comments=0`, chạy hai lần liên tiếp, không ghi vào dữ liệu gốc.

| Request | Có ảnh | Ảnh gửi | Lỗi | Nghi vấn Jev |
| ---: | ---: | ---: | ---: | ---: |
| 26 | 8 | 11 | 0 | 19 |

- Token Jev báo ở lần chạy thứ hai: request có ảnh 18 775 vào / 1 166 ra (8 request), request chỉ có chữ 28 556 vào / 2 664 ra (18 request). Trung bình khoảng 2 350 token đầu vào mỗi request có ảnh; đó là cả request (ảnh, chữ và câu hỏi). Phản hồi không báo riêng token của ảnh nên không tách được.
- Nghi vấn theo nguồn: 6 lời nói, 10 OCR, 2 thumbnail, 1 tiêu đề (19). Trong 10 nghi vấn OCR, chỉ 2 mục có ảnh kèm theo (`seg_0002:ocr`, `seg_0004:ocr`); các mục còn lại thuộc đoạn không có keyframe trong timeline và chỉ gửi chữ. Dòng "CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ" (OCR nhiễu dấu) xuất hiện ở cả hai nhóm, ví dụ `frames/000014.jpg`. Đoạn `seg_0001` chỉ có ảnh sinh một request `visual`, không bị giữ.
- Cả 8 request có ảnh đều không lỗi.
- Chưa đối chiếu độ chính xác của nghi vấn bằng người; số trên chỉ xác nhận request có ảnh chạy được và sinh nghi vấn đúng loại nguồn.

## T65: Đơn vị thống kê và giá niêm yết

Đối chiếu tài liệu công khai ngày 21/11/2026, không gọi thêm API suy luận:

- [Models](https://docs.typesafe.ai/models) niêm yết Jev 1.13 và 1.14 ở mức **0,042 USD mỗi triệu token đầu vào**: “You pay per input token. Output tokens are free.” Đây là đơn giá USD, không phải công thức quy đổi credit hay số dư tài khoản.
- [OpenAPI](https://api.typesafe.ai/openapi.json), được [Swagger](https://api.typesafe.ai/docs) trỏ tới, chỉ liệt kê `/v1/models` và `/v1/systemone`. `Usage` trả `input_tokens` (token đầu vào tính phí) và `output_tokens`; không có trường credit hay API số dư được công bố trong schema này.
- Theo quyết định ngày 21/11/2026, chỉ cộng riêng token vào/ra hợp lệ do TypeSafe báo; h4wk không tự đếm hoặc ước tính. Trường không có số hợp lệ trả `null`, lượt gọi vẫn được tính. Settings tổng hợp theo kỳ và nguồn; Dashboard tổng hợp tháng hiện tại theo giờ Việt Nam. Không hiển thị USD, credit, hạn mức hay số dư Jev.
