# Checkpoint C: kiểm timeline của ba video thật

Kiểm bởi AI (@reviewer), ngày 21/11/2026. Chỉ đọc dữ liệu đã thu; không gọi API, không ghi vào bản thu.

**Kết luận: chưa đánh dấu đạt Checkpoint C.** 14/14 đoạn có lời khớp chính xác biên đầu/cuối và văn bản khi ghép các mục `transcripts/stt.vi.json`; đoạn mở 0–0 chỉ có hình, trước mục STT đầu tiên 0,08 s. Đây là kiểm tra khớp với transcript đã lưu, không phải nghe lại âm thanh độc lập. Các mốc đều trong độ dài proxy (100,821 / 127,101 / 167,701 s theo thứ tự bảng). OCR chữ chèn lớn thường giữ nghĩa, nhưng sai dấu/ký tự lặp lại trên cả ba video, hai khung có chữ nhỏ/nền phức tạp sinh chuỗi nhiễu. Trong 6 khung có mô tả Gemini đã xem, 5 khung có cue trích đúng chữ hiện trên ảnh và khung mở không có cue là phù hợp; các nhãn diễn giải như “kích động” không được xác nhận chỉ từ khung. Hai bản thu còn lại không có mô tả VLM cấp đoạn; không tính là âm tính, cũng không chấm cue.

## Mẫu 15 đoạn

Cả ba manifest ghi mức `full`. `1RUJ_6eruwA` dùng bản `20261120T132008`; hai video còn lại dùng bản `20261120T133043`. Chọn các đoạn rải từ đầu đến cuối, ưu tiên phủ hết những mô tả Gemini hiện có; mẫu không ngẫu nhiên. OCR đối chiếu trên khung nêu trong bảng, không đại diện cho mọi khung của từng đoạn. Tên JPEG viết gọn, đều trong thư mục `frames/` của bản phái sinh tương ứng.

| Video | Đoạn | Giây | Khung | OCR đối chiếu với hình | Cues và ghi chú |
|---|---|---|---|---|---|
| 1RUJ_6eruwA | seg_0001 | 0,00–0,00 | 000001 | Không có OCR; không thấy chữ rõ | Gemini: rỗng, phù hợp; đoạn chỉ có hình |
| 1RUJ_6eruwA | seg_0002 | 0,08–12,62 | 000014 | Đọc năm và hai dòng chữ chèn; lỗi như `CỐC` thay `CÓC`, `CHĨNH` thay `CHÍNH` | Gemini: chữ được dẫn đúng trên cả 000014, 000026, 000181, 000315; là chữ chèn, không phải biểu ngữ vật lý |
| 1RUJ_6eruwA | seg_0004 | 13,38–29,70 | 000586 | Đọc được ý hai dòng, nhưng `DUYỀN` thay `QUYỀN` và lỗi dấu | Gemini dẫn đúng chữ chèn ở chân ảnh |
| 1RUJ_6eruwA | seg_0008 | 69,34–78,46 | 001745 | Đúng ý; sai `NGƯDI`, `DẢN`, `BỔ` | Không có mô tả VLM; ảnh vẫn có chữ chèn |
| 1RUJ_6eruwA | seg_0012 | 97,04–100,44 | 002431 | Đúng ý; sai `CỐC`, `DẢN`, `KỀ` | Không có mô tả VLM; ảnh vẫn có chữ chèn |
| AiOTmCSFs4s | seg_0001 | 0,14–11,04 | 000014 | Đúng cả ba dòng chữ chèn về hội nghị Pháp ngữ | Không có mô tả VLM |
| AiOTmCSFs4s | seg_0004 | 30,08–38,64 | 000763 | Đúng ý tiêu đề; `giữra` thay `giữa` | Không có mô tả VLM |
| AiOTmCSFs4s | seg_0008 | 67,88–79,92 | 001710 | Đọc được ý biển xanh, nhưng `TỔ`/`KHÚNG` sai dấu và có chuỗi số nhiễu | Không có mô tả VLM; biển vật lý và tiêu đề chèn là hai phần khác nhau |
| AiOTmCSFs4s | seg_0012 | 98,94–110,14 | 002475 | Biển xanh trên ảnh còn chữ, OCR rụng phần cuối (`KHÙNG B`); tiêu đề lệch dấu | Không có mô tả VLM |
| AiOTmCSFs4s | seg_0015 | 122,78–126,94 | 003079 | Biển bị cắt ở mép nên OCR chỉ đọc được đầu câu; tiêu đề thiếu ký tự và dấu | Không có mô tả VLM |
| Tb_Kf0nDuK0 | seg_0001 | 0,00–11,92 | 000014 | Đúng cả ba dòng chữ chèn về Bắc Kinh và chủ quyền biển đảo | Không có mô tả VLM |
| Tb_Kf0nDuK0 | seg_0005 | 39,56–47,90 | 000992 | Đúng ý; `tru tiên` thay `ưu tiên` | Không có mô tả VLM |
| Tb_Kf0nDuK0 | seg_0010 | 86,10–97,76 | 002154 | Đúng ý; thiếu chữ `i` ở `với` | Không có mô tả VLM |
| Tb_Kf0nDuK0 | seg_0015 | 135,72–144,38 | 003399 | Đọc được ý tiêu đề và một phần chữ nền hội trường; nhiều cụm nhiễu, `VỀT NAM-TRUNGOUÔC` sai | Không có mô tả VLM |
| Tb_Kf0nDuK0 | seg_0018 | 163,24–167,42 | 004084 | Chữ chèn giữ ý; OCR chữ nhỏ trên màn hình sinh nhiều chuỗi vô nghĩa | Không có mô tả VLM |

**Cần kiểm tiếp:** mô tả và cues cho hai video chưa có đầu ra VLM. Chỉ chạy lại tầng phân tích trên timeline hiện có không bổ sung `visual`; cần chạy bước mô tả ảnh/tạo timeline trước khi chấm cue. OCR trên chữ nhỏ cần đối chiếu ảnh gốc trước khi trích dẫn; mẫu này không đủ để suy ra tỷ lệ lỗi cho toàn bộ tập video.
