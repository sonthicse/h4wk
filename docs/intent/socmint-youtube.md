# Statement of intent: công cụ SOCMINT cho YouTube (bản demo bài tập lớn)

> Xác nhận ngày 2026-11-18 qua phỏng vấn (`interview-me`), cập nhật cùng ngày khi viết spec và sau vòng review.
> Mô tả gốc đầy đủ nằm ở [.tmp/MO_TA_DU_AN.md](../../.tmp/MO_TA_DU_AN.md). Tài liệu này thu hẹp phạm vi đó cho bản demo và được ưu tiên khi hai tài liệu mâu thuẫn.

## Kết quả mong muốn

Một luồng K1 (bôi nhọ đối tượng) đa phương thức chạy trọn từ đầu đến cuối:

1. Thu thập qua lớp adapter. Mỗi nguồn (yt-dlp, YouTube Data API, Supadata) là một module lắp thêm hoặc tháo ra được. Adapter khai báo loại dữ liệu nó lấy được, lưu dữ liệu thô nguyên văn và chuyển về mô hình dữ liệu chung (kênh, video, transcript, comment, file media). Mỗi loại dữ liệu lấy từ một nguồn theo thứ tự ưu tiên; nguồn khác chỉ dùng khi nguồn trước lỗi. Giao diện chỉnh nguồn cho phép bật/tắt nguồn, nhập API key, đổi thứ tự ưu tiên và kiểm tra kết nối. Comment được thu toàn bộ, kể cả reply.
2. Lưu bằng chứng. Mỗi lần thu có manifest ghi SHA-256 của từng file và kiểm tra toàn vẹn được. Bản thu được khoá để chống sửa nhầm. Nguồn gốc dữ liệu ghi ở mức từng lần gọi nguồn.
3. Transcript tiếng Việt có mốc thời gian.
4. Phân tích hình ảnh. Khung hình được trích theo mức thay đổi, sau đó:
   - OCR đọc chữ chèn trên hình, ví dụ "[Tên] LỪA ĐẢO" hay chữ trên thumbnail;
   - keyframe và thumbnail được gửi thẳng cho Jev cùng chữ OCR (không còn bước VLM mô tả ảnh; quyết định ngày 21/11/2026);
   - khuôn mặt trong hình được so với ảnh khuôn mặt mẫu của đối tượng, bằng model chạy trên máy;
   - hình được so với ảnh mẫu hay bị dùng lại của đối tượng (ảnh chân dung quen thuộc, logo).
5. Timeline đa phương thức: lời nói, chữ trên hình và mô tả khung hình gắn chung một mốc thời gian.
6. Phân tích K1 trong module `analysis`, trên timeline, tiêu đề, mô tả, thumbnail và comment. Tầng tĩnh khớp tên và biệt danh không phân biệt dấu, kết hợp từ điển từ xúc phạm. Tầng Jev trả về phân loại, mức độ và đối tượng bị nhắm tới; kết luận theo video tính bằng quy tắc. Một đoạn chỉ có ảnh chế mà không ai nhắc tên vẫn được phân tích, nhờ khuôn mặt mẫu, ảnh mẫu hoặc ngữ cảnh của cả video. Yêu cầu ban đầu là LLM và VLM dùng được nhiều nhà cung cấp; Thi đã đảo yêu cầu này ngày 21/11/2026: Jev (TypeSafe) là nhà cung cấp AI duy nhất, nhận cả ảnh (xem SPEC.md 10.4).
7. Hàng đợi rà soát.

Ngoài luồng trên còn có watchlist kênh: hệ thống phát hiện video mới qua RSS, tự thu, tự phân tích và đưa nghi vấn vào hàng đợi.

## Người dùng

Hai thành viên nhóm trong vai analyst, Thi là người chịu trách nhiệm chính. Người cần thuyết phục là người chấm trong buổi demo.

## Vì sao làm bây giờ

Đây là bài tập lớn, demo vào khoảng cuối tháng 12/2026 (6 tuần tính từ 2026-11-18).

## Thế nào là thành công

Demo chạy được là tiêu chí chính; báo cáo phương pháp đứng thứ hai. Buổi demo gồm ba màn:

1. Dữ liệu chuẩn bị sẵn với 10–20 video thật. Video phát nhảy đúng tới đoạn bị nghi. Hàng đợi có nghi vấn từ lời nói, từ chữ trên hình và từ hình ảnh, trong đó có ít nhất một nghi vấn hình ảnh ở đoạn không ai nhắc tên. Analyst duyệt nghi vấn ngay trên giao diện.
2. Dán link trực tiếp: hệ thống xử lý ngay tại chỗ một video ngắn.
3. Watchlist: một kênh tin tức đang theo dõi đăng video mới, hệ thống tự phát hiện và tự xử lý video đó, mục tiêu là trong khoảng 10 phút.

Buổi demo cũng trình diễn giao diện chỉnh nguồn để cho thấy kiến trúc adapter.

## Ràng buộc

- Nhóm có nhiều thời gian nên thời gian không phải ràng buộc; các mốc thời gian xử lý là mục tiêu, không bắt buộc. Việc viết code có AI coding agent hỗ trợ.
- Tiền API (Jev, speech-to-text, Supadata) không giới hạn.
- Backend Python (FastAPI), frontend React, giao diện tiếng Anh. Cả hai thành viên thạo Python nhưng yếu frontend, nên cần đọc lại code do agent sinh ra để trả lời được câu hỏi của người chấm.
- Chạy trực tiếp trên máy, không dùng Docker.
- Khớp khuôn mặt chỉ so với các đối tượng đã khai báo, chạy trên máy, không lưu đặc trưng của khuôn mặt không khớp, và khi demo dùng ảnh chân dung công khai của nhân vật công chúng là đối tượng (đổi ngày 2026-11-21, xem SPEC §13).
- Comment được gửi nguyên văn cho Jev.

## Ngoài phạm vi

- Kịch bản K2 (tin giả), K3 (mạng lưới kênh), K4 (xác minh, tìm kiếm ngữ nghĩa), K5 (hình ảnh vi phạm như cờ, biểu tượng); đồ thị mạng lưới kênh.
- Xuất báo cáo, để làm sau.
- Ảnh chụp trang.
- Nhận diện danh tính người bất kỳ qua khuôn mặt.
- Watchlist theo từ khoá, đối tượng, video, playlist. V1 chỉ theo dõi kênh, với sự kiện video mới.
- Thu lại theo lịch thưa dần, ghi livestream, phát hiện đổi tên/avatar kênh, tự nâng mức thu.
- Khôi phục từ Internet Archive.
- Ghi nguồn gốc tới từng trường dữ liệu.
- Đánh giá precision/recall chính thức.

## Lịch sử thay đổi

Ngày 2026-11-18, khi viết spec, nhóm đổi các điểm sau so với bản xác nhận lúc phỏng vấn:

- Giao diện viết bằng tiếng Anh.
- Thu toàn bộ comment và đưa comment vào phân tích K1.
- Comment gửi nguyên văn cho Jev; yêu cầu nhiều nhà cung cấp LLM/VLM đã bị đảo ngày 21/11/2026.
- Bỏ ảnh chụp trang và xuất báo cáo khỏi V1.
- Module phân tích đặt tên là `analysis`.
- Bỏ giới hạn 120 giờ công.

Cùng ngày, sau vòng review tài liệu:

- Thi là người chịu trách nhiệm chính; task của Thi không phải chờ task của Bảo.
- Các mốc thời gian xử lý chuyển thành mục tiêu, không bắt buộc.
- Bỏ phương án làm đơn giản ở cuối tuần 4; Settings giữ đủ 7 mục.
- Thêm khớp khuôn mặt và khớp ảnh mẫu, và cho phép phân tích hình ảnh dựa trên ngữ cảnh cả video. Khớp khuôn mặt đảo ngược quy định "không nhận diện khuôn mặt" ở mục 13 và 14 của mô tả gốc, nên được giới hạn như ở phần Ràng buộc.
- Cơ chế khoá bản thu chỉ chống sửa nhầm, và dựng lại database có thể làm mất watchlist. Nhóm chấp nhận hai hạn chế này trong giai đoạn thử nghiệm.

Cùng ngày, sau phần 1 của spike T2:

- Chỉ thu phụ đề tiếng Việt, không thu phụ đề mọi ngôn ngữ.
- Nhóm không có kênh YouTube riêng. Màn 3 theo dõi kênh tin tức nên chỉ trình diễn phát hiện và tự xử lý video mới, không trình diễn nghi vấn mới.

Cùng ngày, khi duyệt quy ước dữ liệu:

- Mọi thời gian dùng giờ Việt Nam (UTC+07:00) thay cho UTC.
- Phân tích lại một video thì phải rà soát lại toàn bộ nghi vấn; bỏ cơ chế giữ quyết định cũ theo `key`.
- `id` của nghi vấn có dạng `f_<ULID>`, duy nhất trong cả case, để quyết định rà soát trỏ đúng nghi vấn.
- Mô hình phân tích từ chối quyết định Reject không có lý do.

Ngày 2026-11-19, khi gộp phần của Bảo:

- Từ điển tầng tĩnh chia nhóm theo danh sách thông tin xâm phạm an ninh quốc gia; mỗi nhóm gắn một category của mô hình phân tích.
- Mô hình phân tích thêm hai category `incitement` (kích động, chia rẽ, bạo lực) và `state_secret` (bí mật nhà nước).
- Đối tượng thường là lãnh đạo Đảng và Nhà nước; tầng tĩnh vẫn chỉ chạy ở vùng nhắc tên đối tượng.
- Viết tắt của đối tượng so không phân biệt hoa thường.
- Bỏ khái niệm case: cả hệ thống là một cuộc theo dõi duy nhất, vì demo chỉ dùng một case. Đối tượng, watchlist, video, nghi vấn và nhật ký dùng chung; mô hình phân tích bỏ `case_id`.
- Watchlist mặc định theo dõi bốn kênh ví dụ ở mức `metadata`: Việt Tân, BBC News Tiếng Việt, Chân Trời Mới Media, Luật Khoa tạp chí.
- MÃ´ hÃ¬nh dá»¯ liá»u chung: comment có thêm `author_name` (tên hiển thị lúc thu).
- Chốt model theo spike T3: Whisper large-v3, PaddleOCR PP-OCRv5 chạy CPU, DINOv2 ViT-S/14, InsightFace buffalo_l. Đạt Checkpoint A; từ đây mọi thay đổi quy ước dữ liệu phải được người phụ trách chính đồng ý.

Ngày 2026-11-22:

- Đăng nhập bằng một tài khoản duy nhất đặt trong `.env`, bỏ hai tài khoản trong database.
- Mọi cấu hình người dùng gom về `config/`: thêm `entities.toml` (thay `data/entities.json`) và `watchlist.toml` (danh sách kênh, trước chỉ nằm trong database). Mô hình cấu hình thêm hai định dạng này.
- Bỏ đối tượng mặc định "Đảng và Nhà nước Việt Nam" và bốn kênh watchlist ví dụ, để ai cũng dùng được công cụ với đối tượng và kênh của mình.
- Gỡ câu "The Party, State or regime counts as attacked even when not named" khỏi prompt Jev; lưu ở `docs/notes/jev-prompt.md`.
- Bỏ lệnh `h4wk schema export` và thư mục `docs/contracts/`: không còn nơi nào dùng các file JSON Schema này.
- Đổi cách gọi "hợp đồng" dữ liệu thành "quy ước".
- Bỏ CLI `h4wk`: API tự khởi tạo `data/` và `config/` khi khởi động; phân tích lại bằng nút Re-analyze trên web; bỏ `reindex` và `verdict`.
- Mỗi kênh watchlist có luồng xử lý riêng, số luồng mỗi kênh đặt ở Settings → Watchlist.
- Thêm vi phạm xét theo nội dung, không cần đối tượng: `violence`, `hate`, `forgery` (thêm vào mô hình phân tích) và `state_secret`. Chỉ lấy các mục trong danh sách thông tin xâm phạm an ninh quốc gia mà nội dung tự gây hại (kích động bạo lực, khủng bố, thù hận dân tộc và tôn giáo, lộ bí mật, giả mạo giấy tờ và deepfake); không làm các mục nhắm vào phát ngôn chính trị. Nghi vấn loại này có `entity` trống.
- Cố định thư mục `data/`, `config/` và model STT `large-v3`; `.env` chỉ còn tài khoản và API key.
- Supadata không còn nhờ AI tạo transcript (đã tốn 140 credit, vượt gói 100/tháng); chỉ lấy phụ đề YouTube có sẵn. Video không có phụ đề dùng speech-to-text trên máy.
- Bỏ `config/analysis.toml`: thứ tự transcript, số request Jev song song cố định trong code; Jev luôn xét mọi comment, mỗi comment một request; khớp khuôn mặt và ảnh mẫu chỉ chạy khi đối tượng có ảnh mẫu (bỏ ảnh là tắt).
