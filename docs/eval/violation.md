# Đánh giá câu hỏi vi phạm theo nội dung (2026-11-22)

Câu hỏi `violation` của Jev (`analysis/jev.py`) phân loại `violence`, `hate`, `state_secret`, `forgery` hoặc `none`, không cần đối tượng. Đo ở chế độ chưa khai báo đối tượng (chỉ hỏi `violation` và `severity`), mỗi câu một request. Quy tắc giữ: tổng xác suất các danh mục vi phạm ≥ 0,6, danh mục là cái cao nhất.

## Kết quả

| Tập | Prompt | Precision | Recall | Câu bị đánh dấu sai |
| --- | --- | ---: | ---: | ---: |
| Tập có nhãn, 96 câu | v1 | 44/44 | 44/45 | 0 |
| Tập có nhãn, 96 câu | v2, 2 lần chạy | 44/44 | 44/45 | 0 |
| 300 câu thật, chưa nhãn | v1 | — | — | 4/300 |
| 300 câu thật, chưa nhãn | v2, 2 lần chạy | — | — | 0/300 và 1/300 |

- **Tập có nhãn** (`violation_set.csv`): 45 câu vi phạm (15 violence, 12 hate, 8 state_secret, 10 forgery) và 51 câu không vi phạm nhưng dễ nhầm: chỉ trích chính quyền gay gắt, chửi lãnh đạo, tin tức về bạo loạn, khủng bố, deepfake, bàn về lịch sử, tôn giáo, dân tộc, nói quá ("tức muốn đập cái ti vi"), kêu gọi biểu tình ôn hoà. Câu do Claude viết, nhãn do Claude gán, chưa có người duyệt.
- Câu bị bỏ sót: "Bán con dấu giả của các sở ban ngành…" (forgery, tổng 0,37–0,57). Hai câu hate có kêu gọi đốt, đập phá bị xếp vào violence; vẫn là vi phạm nên không tính là sai ở cột precision/recall.
- **300 câu thật**: lấy ngẫu nhiên từ 2 529 câu đã thu (291 comment, 5 tiêu đề, 4 lời nói), chủ yếu từ các kênh chính trị đang theo dõi. Claude đọc từng câu bị đánh dấu và các câu có tổng xác suất từ 0,15: không có câu nào là vi phạm theo nội dung, nên mọi câu bị đánh dấu đều là báo động sai. Recall trên dữ liệu thật chưa đo được vì mẫu không có vi phạm thật.

## Đã điều chỉnh

Prompt v1 đánh dấu 4/300 câu thật, cả 4 đều sai: định kiến vùng miền ("Bắc kỳ… chưa thấm đòn"), câu tục chửi sư, chửi người dân "ngu muội", ẩn dụ "nuôi đàn khuyển dữ". Prompt v2:

- Hướng dẫn chung: chửi, rủa, mong gặp quả báo, đùa tục, ẩn dụ nhắm vào quan chức, sư, người bình luận là `none` trừ khi kêu gọi gây hại thật; định kiến vùng miền hay phe chính trị là `none`.
- `violence`: chỉ lời kêu gọi, kế hoạch, hướng dẫn thật hoặc ca ngợi một vụ tấn công thật; không tính lối nói ví von.
- `hate`: phi nhân hoá, hoặc kêu gọi gây hại, trục xuất, phân biệt với cả một dân tộc, tôn giáo, quốc tịch.
- Quy tắc giữ đổi từ "danh mục cao nhất ≥ 0,5" sang "tổng các danh mục ≥ 0,6", để câu vừa bạo lực vừa thù hận (xác suất chia đôi) không lọt, đồng thời cắt các câu sát ngưỡng.

Jev không tất định: câu "Thằng này thiến chưa bọn sư phải thiến…" có tổng 0,44 ở lần chạy này và 0,63 ở lần chạy khác. Ngưỡng 0,7 loại được câu này nhưng làm mất thêm 1 câu vi phạm trên tập có nhãn.

## Chạy lại

```bash
cd backend
uv run python ../docs/eval/violation_run.py ../docs/eval/violation_set.csv /tmp/out.jsonl
python ../docs/eval/violation_score.py /tmp/out.jsonl 0.6
```

Chi phí cả đợt đo (6 lượt, 1 188 request): khoảng 1,13 triệu token đầu vào.
