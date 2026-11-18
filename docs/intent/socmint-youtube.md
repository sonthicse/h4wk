# Statement of intent: công cụ SOCMINT cho YouTube (bản demo bài tập lớn)

> Xác nhận ngày 2026-11-18 qua phỏng vấn (`interview-me`), cập nhật cùng ngày khi viết spec và sau vòng review.
> Mô tả gốc đầy đủ nằm ở [.tmp/MO_TA_DU_AN.md](../../.tmp/MO_TA_DU_AN.md). Tài liệu này thu hẹp phạm vi đó cho bản demo và được ưu tiên khi hai tài liệu mâu thuẫn. Chi tiết kỹ thuật nằm ở [SPEC.md](../../SPEC.md), và SPEC.md được ưu tiên hơn cả hai.

## Kết quả mong muốn

Một luồng K1 (bôi nhọ đối tượng) đa phương thức chạy trọn từ đầu đến cuối:

1. Thu thập qua lớp adapter. Mỗi nguồn (yt-dlp, YouTube Data API, Supadata) là một module lắp thêm hoặc tháo ra được. Adapter khai báo loại dữ liệu nó lấy được, lưu dữ liệu thô nguyên văn và chuyển về mô hình dữ liệu chung (kênh, video, transcript, comment, file media). Mỗi loại dữ liệu lấy từ một nguồn theo thứ tự ưu tiên; nguồn khác chỉ dùng khi nguồn trước lỗi. Giao diện chỉnh nguồn cho phép bật/tắt nguồn, nhập API key, đổi thứ tự ưu tiên và kiểm tra kết nối. Comment được thu toàn bộ, kể cả reply.
2. Lưu bằng chứng. Mỗi lần thu có manifest ghi SHA-256 của từng file và kiểm tra toàn vẹn được. Bản thu được khoá để chống sửa nhầm. Nguồn gốc dữ liệu ghi ở mức từng lần gọi nguồn.
3. Transcript tiếng Việt có mốc thời gian.
4. Phân tích hình ảnh. Khung hình được trích theo mức thay đổi, sau đó:
   - OCR đọc chữ chèn trên hình, ví dụ "[Tên] LỪA ĐẢO" hay chữ trên thumbnail;
   - VLM (qua API) mô tả hình ảnh và liệt kê dấu hiệu xúc phạm như ảnh ghép, ảnh chế, ảnh đặt cạnh hình tiêu cực;
   - khuôn mặt trong hình được so với ảnh khuôn mặt mẫu của đối tượng, bằng model chạy trên máy;
   - hình được so với ảnh mẫu hay bị dùng lại của đối tượng (ảnh chân dung quen thuộc, logo).
5. Timeline đa phương thức: lời nói, chữ trên hình và mô tả khung hình gắn chung một mốc thời gian.
6. Phân tích K1 trong module `analysis`, trên timeline, tiêu đề, mô tả, thumbnail và comment. Tầng tĩnh khớp tên và biệt danh không phân biệt dấu, kết hợp từ điển từ xúc phạm. Tầng LLM trả về đầu ra có cấu trúc gồm phân loại, mức độ, lý do, trích dẫn và mốc thời gian. Một đoạn chỉ có ảnh chế mà không ai nhắc tên vẫn được phân tích, nhờ khuôn mặt mẫu, ảnh mẫu hoặc ngữ cảnh của cả video. LLM và VLM dùng được nhiều nhà cung cấp, kể cả các nhà cung cấp Trung Quốc.
7. Hàng đợi rà soát.

Ngoài luồng trên còn có watchlist kênh: hệ thống phát hiện video mới qua RSS, tự thu, tự phân tích và đưa nghi vấn vào hàng đợi.

## Người dùng

Hai thành viên nhóm trong vai analyst, Thi là người chịu trách nhiệm chính. Người cần thuyết phục là người chấm trong buổi demo.

## Vì sao làm bây giờ

Đây là bài tập lớn, demo vào khoảng cuối tháng 12/2026 (6 tuần tính từ 2026-11-18).

## Thế nào là thành công

Demo chạy được là tiêu chí chính; báo cáo phương pháp đứng thứ hai. Buổi demo gồm ba màn:

1. Case chuẩn bị sẵn với 10–20 video thật. Video phát nhảy đúng tới đoạn bị nghi. Hàng đợi có nghi vấn từ lời nói, từ chữ trên hình và từ hình ảnh, trong đó có ít nhất một nghi vấn hình ảnh ở đoạn không ai nhắc tên. Analyst duyệt nghi vấn ngay trên giao diện.
2. Dán link trực tiếp: hệ thống xử lý ngay tại chỗ một video ngắn.
3. Watchlist: đăng video lên kênh thử nghiệm, nghi vấn mới tự xuất hiện trong hàng đợi, mục tiêu là trong khoảng 10 phút.

Buổi demo cũng trình diễn giao diện chỉnh nguồn để cho thấy kiến trúc adapter.

## Ràng buộc

- Nhóm có nhiều thời gian nên thời gian không phải ràng buộc; các mốc thời gian xử lý là mục tiêu, không bắt buộc. Việc viết code có AI coding agent hỗ trợ.
- Tiền API (LLM, VLM, speech-to-text, Supadata) không giới hạn.
- Backend Python (FastAPI), frontend React, giao diện tiếng Anh. Cả hai thành viên thạo Python nhưng yếu frontend, nên cần đọc lại code do agent sinh ra để trả lời được câu hỏi của người chấm.
- Chạy trực tiếp trên máy, không dùng Docker.
- Khớp khuôn mặt chỉ so với đối tượng của case, chạy trên máy, không lưu đặc trưng của khuôn mặt không khớp, và khi demo dùng khuôn mặt của thành viên nhóm.
- Comment được gửi nguyên văn cho nhà cung cấp AI. Settings chỉ cho chọn nhà cung cấp, không chọn theo quốc gia.

## Ngoài phạm vi

- Kịch bản K2 (tin giả), K3 (mạng lưới kênh), K4 (xác minh, tìm kiếm ngữ nghĩa), K5 (hình ảnh vi phạm như cờ, biểu tượng); đồ thị mạng lưới kênh.
- Xuất báo cáo, để làm sau.
- Ảnh chụp trang.
- Nhận diện danh tính người bất kỳ qua khuôn mặt.
- Watchlist theo từ khoá, đối tượng, video, playlist. V1 chỉ theo dõi kênh, với sự kiện video mới.
- Thu lại theo lịch thưa dần, ghi livestream, phát hiện đổi tên/avatar kênh, tự nâng mức thu.
- Khôi phục từ Internet Archive.
- Ghi nguồn gốc tới từng trường dữ liệu.
- Đánh giá precision/recall chính thức. Nếu còn thời gian, chỉ làm một bảng so sánh nhỏ giữa tĩnh và LLM (khoảng 50 đoạn) cho báo cáo môn học.

## Lịch sử thay đổi

Ngày 2026-11-18, khi viết spec, nhóm đổi các điểm sau so với bản xác nhận lúc phỏng vấn:

- Giao diện viết bằng tiếng Anh.
- Thu toàn bộ comment và đưa comment vào phân tích K1.
- LLM/VLM dùng nhiều nhà cung cấp; comment gửi nguyên văn; Settings không có lựa chọn theo quốc gia.
- Bỏ ảnh chụp trang và xuất báo cáo khỏi V1.
- Module phân tích đặt tên là `analysis`.
- Bỏ giới hạn 120 giờ công.

Cùng ngày, sau vòng review tài liệu:

- Thi là người chịu trách nhiệm chính; task của Thi không phải chờ task của Bảo.
- Các mốc thời gian xử lý chuyển thành mục tiêu, không bắt buộc.
- Bỏ phương án làm đơn giản ở cuối tuần 4; Settings giữ đủ 7 mục.
- Thêm khớp khuôn mặt và khớp ảnh mẫu, và cho phép phân tích hình ảnh dựa trên ngữ cảnh cả video. Khớp khuôn mặt đảo ngược quy định "không nhận diện khuôn mặt" ở mục 13 và 14 của mô tả gốc, nên được giới hạn như ở phần Ràng buộc.
- Cơ chế khoá bản thu chỉ chống sửa nhầm, và dựng lại database có thể làm mất tài khoản và watchlist. Nhóm chấp nhận hai hạn chế này trong giai đoạn thử nghiệm.

Cùng ngày, sau phần 1 của spike T2:

- Chỉ thu phụ đề tiếng Việt, không thu phụ đề mọi ngôn ngữ.
