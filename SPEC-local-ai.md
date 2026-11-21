# Spec Delta: AI cục bộ và Jev cho mọi văn bản

Status: approved (2026-11-21)

Kế hoạch: [tasks/plan.md](tasks/plan.md) Phase 6c (T51–T57).

Spec gốc: [SPEC.md](SPEC.md) §10.4 `ai-gateway`, §10.5 bước 5 (VLM), §10.6 bước 3–4, §13. Sau khi làm xong, nội dung của delta này được gộp vào SPEC.md và dòng `Status` đổi thành `implemented`.

## Mục tiêu

Cho mô hình chạy trên máy nhóm (Ollama, GPU T1000 8 GB) làm hai tác vụ AI còn đang dùng cloud: mô tả ảnh (`media.vision`) và kết luận theo video (`analysis.video_verdict`). Mọi việc phân loại văn bản (tiêu đề, mô tả, OCR, mô tả ảnh) chuyển sang Jev với cấu hình đã tinh chỉnh, nên tác vụ AI `analysis.classify` bị bỏ. Nhà cung cấp cloud vẫn được cấu hình làm tuyến dự phòng để trình diễn khả năng hỗ trợ nhiều nhà cung cấp.

Quyết định của Thi ngày 2026-11-21:

- Ollama chạy VLM và LLM kết luận; Jev giữ nguyên là API cloud.
- Giữ Gemini, OpenRouter, Anthropic trong cấu hình làm tuyến sau Ollama.
- Gửi VLM toàn bộ keyframe và thumbnail, không lọc; chấp nhận xử lý chậm.
- Giữ Supadata.
- Không hiện lý do kỹ thuật bên trong (vd `Jev: insult p=0.91`) cho người dùng.
- Khớp khuôn mặt giữ OpenCV YuNet + SFace đang có trên `main`.
- `base_url` mặc định của Ollama trong file mẫu là `http://localhost:11434/v1`; khi demo, Ollama chạy ở máy GPU riêng trong LAN (ghi trong `config/ai.toml`, không commit), không chạy cùng máy backend.

## Hành vi hiện tại

- `ai-gateway` có ba tác vụ AI: `analysis.classify`, `analysis.video_verdict`, `media.vision`; cấu hình thật đang định tuyến cả ba qua Gemini → OpenRouter → Anthropic.
- Jev chỉ xét lời nói và comment, câu hỏi `category`/`target`/`severity`, giữ nghi vấn khi tổng xác suất các danh mục vi phạm ≥ 0,5. Trên bộ test 119 mục: P 0,615 / R 0,960.
- Tiêu đề, mô tả, OCR, mô tả ảnh và thumbnail đi qua LLM (`analysis.classify`), chỉ những mục có dấu hiệu.
- `vision.json` chỉ được ghi khi đã mô tả xong mọi ảnh; khoá cache gồm hash của toàn bộ `ai.toml`.
- Mỗi request AI có thời gian chờ 120 giây.
- Giao diện hiện trường `reason` của nghi vấn.

## Hành vi mới

### 1. Nhà cung cấp `ollama` (đã làm ở nhánh `feat/ollama-provider`)

Hợp đồng C5 có loại nhà cung cấp `ollama`: bắt buộc `base_url`, không cần key, dùng lại adapter `openai_compat`. Trang Settings thêm được nhà cung cấp Ollama, không có ô API key.

### 2. Mô tả ảnh cục bộ (`media.vision`)

- Tuyến mặc định: `ollama/qwen3-vl:4b` (`vision = true`, `structured = false`), sau đó Gemini, OpenRouter, Anthropic.
- Prompt thêm câu “Trả lời ngắn gọn, không cần suy luận dài.” (đo ngày 21/11: không có câu này, 1/6 ảnh lặp từ tới hết context và trả rỗng sau 281 giây).
- Request tới nhà cung cấp `ollama` có thời gian chờ 300 giây và giới hạn độ dài đầu ra (`max_tokens` 1024).
- `vision.json` được ghi sau mỗi ảnh mô tả xong, nên job bị dừng giữa chừng chạy lại chỉ mô tả các ảnh còn thiếu.
- Khoá cache của một ảnh gồm hash ảnh, prompt, `provider` và `model` đã mô tả nó. Sửa tuyến của tác vụ khác (vd `analysis.video_verdict`) không làm mô tả lại ảnh.

### 3. Kết luận theo video cục bộ (`analysis.video_verdict`)

- Tuyến mặc định: `ollama/qwen3-vl:4b`, sau đó các nhà cloud. Dùng chung model với VLM để không phải đổi model trong 8 GB VRAM.
- Prompt và hợp đồng `VideoVerdict` giữ nguyên.

### 4. Jev phân loại mọi văn bản

- Áp cấu hình R10 (`data/eval/jev/tune/final_questions.json`) cho mọi request Jev:
  - `state` có `protected_targets`, `source_type`, `text`, `video_title`, và ngữ cảnh theo loại (`parent_comment`; `speech_before`/`speech_after`);
  - câu hỏi `category` (criteria dạng `{what, examples}`), `severity`, `is_attack`, `target`;
  - giữ nghi vấn khi `is_attack.noul ≥ 0,5` và `target.choice ≠ "none"`; danh mục và `confidence` lấy từ `category`, `severity` từ `severity`.
  - `protected_targets` và `target.criteria` sinh từ danh sách đối tượng (tên, biệt danh, viết tắt, mô tả nếu có), không viết cứng.
- Nguồn mới gửi Jev, mỗi mục một request:
  - tiêu đề video (`source_kind: title`), mô tả video (`description`);
  - mỗi đoạn timeline có OCR hoặc mô tả ảnh: `text` là các dòng OCR ghép bằng ` | ` (bỏ dòng trùng) cùng mô tả ảnh và `offensive_cues` (`source_kind: ocr` hoặc `visual`, kèm `frame`);
  - mỗi thumbnail có OCR hoặc mô tả ảnh (`source_kind: thumbnail`).
  Như lời nói và comment, Jev xét mọi mục loại này, không chỉ mục có dấu hiệu tên.
- Bỏ tác vụ AI `analysis.classify` và module `analysis/llm.py`. Cấu hình cũ còn tuyến `analysis.classify` được đọc bình thường, tuyến đó bị bỏ qua và ghi cảnh báo (giống `analysis.classify_comment` hiện nay). Trang Settings không còn dòng `analysis.classify`.

### 5. Ẩn lý do kỹ thuật

Giao diện không hiện `reason` của nghi vấn do Jev sinh (danh sách nghi vấn, màn rà soát). `reason` vẫn được ghi trong `findings.json` để tra cứu.

## Tiêu chí thành công

1. Với `config/ai.toml` theo file mẫu mới và Ollama chạy `qwen3-vl:4b`, xử lý một video thật ở mức `full` thì mọi keyframe và thumbnail có mô tả, `vision.json` ghi `provider: ollama`, `model: qwen3-vl:4b`; `data/ai_calls.jsonl` không có lời gọi cloud cho `media.vision`.
2. Dừng worker giữa bước mô tả ảnh rồi chạy lại: các ảnh đã mô tả không được gửi lại (đếm trong `ai_calls.jsonl`).
3. Tắt Ollama thì `media.vision` và `analysis.video_verdict` chuyển sang tuyến cloud kế tiếp (có key) và kết quả ghi đúng `provider`, `model` của tuyến đó.
4. Trên ít nhất 5 video có nghi vấn vi phạm, kết luận do `qwen3-vl:4b` sinh qua gateway có JSON hợp lệ ngay lần đầu hoặc sau lượt sửa, tóm tắt tiếng Việt có dấu, và Thi đánh giá đạt ít nhất 4/5.
5. Đầu ra Jev trên bộ test 119 mục (`data/eval/jev/tune/`) khi chạy qua `analysis/jev.py` mới khớp số liệu R10 (P 0,754 / R 0,920, sai lệch ±0,02 do Jev không tất định).
6. Trên video `1RUJ_6eruwA`, dòng chữ “CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ” trên hình sinh nghi vấn `source_kind: ocr` (hoặc `visual`) từ Jev mà không cần tác vụ `analysis.classify`.
7. Giao diện danh sách nghi vấn và màn rà soát không còn chuỗi `Jev:`.
8. Backend `pytest`, `ruff check`, `ruff format --check`; web `npm run build`, `npm run lint` đều qua. Test không gọi mạng (Jev giả, `FakeProvider`).

Không được thay đổi:

- Hợp đồng `Finding`, `VideoVerdict`, `reviews.jsonl`.
- Jev lỗi thì job vẫn xong, lỗi ghi vào `llm_error`.
- Tầng tĩnh, khớp tên, khớp ảnh mẫu, khớp khuôn mặt.

## Ranh giới (khác so với SPEC.md §11)

- Luôn: giữ adapter cloud trong code và trong `ai.toml.example`; test không gọi Ollama hay Jev thật (lời gọi thật chỉ trong `pytest -m live`).
- Hỏi trước: đổi model mặc định khác `qwen3-vl:4b`; thêm lọc hay giới hạn số ảnh gửi VLM; đổi ngưỡng `is_attack`.
- Không: ghi IP máy GPU vào file được commit; xoá nhánh `analysis.classify` khỏi cấu hình của người dùng mà không cảnh báo.

## Ngoài phạm vi (để sau)

- Lọc hoặc giới hạn số keyframe gửi VLM: Thi chọn gửi hết, chấp nhận chậm.
- Thay Jev bằng LLM cục bộ: Jev vừa tinh chỉnh xong, chưa có lựa chọn cục bộ tương đương.
- Đổi khớp khuôn mặt sang InsightFace: giữ OpenCV.
- Thanh tiến độ “đã mô tả x/y ảnh” trên giao diện job.
- Gán nhãn lại bộ đánh giá Jev bằng người.

## Câu hỏi đã chốt

1. Ollama chạy ở máy GPU riêng, không chung VRAM với Whisper và DINOv2 của backend.
2. Chỉ ẩn `reason` của nghi vấn Jev; nghi vấn tầng tĩnh vẫn hiện nhóm và cụm từ khớp.

## Câu hỏi còn mở

1. Video 342 keyframe mất khoảng 4 giờ cho bước mô tả ảnh. Màn 2 (dán link trực tiếp) chọn video ngắn khi chuẩn bị dữ liệu demo (T36, T37).
