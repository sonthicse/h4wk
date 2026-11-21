# Danh sách task: h4wk V1

Kế hoạch: [plan.md](plan.md). Spec: [SPEC.md](../SPEC.md).

Lệnh dùng chung:

- Test backend: `cd backend && uv run pytest`
- Lint backend: `cd backend && uv run ruff check .`
- Build frontend: `cd web && npm run build && npx tsc --noEmit`

Một task chỉ được coi là xong (Definition of Done) khi test pass và ruff sạch, luồng đã chạy được trước đó vẫn chạy, phần kiểm tra thủ công của task đã làm, và SPEC.md đã được cập nhật nếu task làm thay đổi spec.

Cách đọc phần cuối mỗi task:

- "Phụ thuộc" là task phải xong trước.
- "Tích hợp sau" là task của người kia mà task này cần nối vào. Task vẫn bắt đầu và hoàn thành được trước, bằng bản thu mẫu của T44 hoặc `FakeProvider`; khi task kia xong thì nối vào và chạy lại test.
- Cỡ: S là 1–2 file, M là 3–5 file.

Thi là người chịu trách nhiệm chính. Task của Thi không phải chờ task của Bảo.

## Phase 0: Nền móng và spike

### T1: Scaffold backend và frontend

Tạo `backend/` gồm uv, FastAPI, ruff, pytest và CLI `h4wk` có lệnh `init`. Tạo `web/` gồm Vite, React, TypeScript, Tailwind, shadcn/ui, React Router và TanStack Query, với proxy `/api` sang :8000. Thư mục dữ liệu đọc từ `H4WK_DATA_DIR`, mặc định là `data/` ở gốc repo. File `.gitignore` đã có sẵn ở gốc repo; bổ sung nếu scaffold sinh thêm thư mục cần bỏ qua.

Nghiệm thu:

- [x] `uv run h4wk init` tạo `data/` và `config/*.toml` từ file mẫu.
- [x] `GET /api/health` trả về `{"status":"ok"}`.
- [x] Trang React gọi được `/api/health` qua proxy.

Kiểm tra: `uv run pytest` (có 1 test cho health), `npm run build`, mở :5173 và thấy trạng thái "ok".

File: `backend/pyproject.toml`, `backend/src/h4wk/{cli.py,api/app.py,core/config.py}`, `web/*`, `.gitignore`, `config/*.example`.
Người làm: Thi. Phụ thuộc: không có. Cỡ: M.

### T2: Spike yt-dlp trên WSL và độ trễ RSS

Script tạm đặt trong `docs/spikes/`. Spike gồm ba phần:

1. Dùng yt-dlp tải metadata, phụ đề tiếng Việt, comment và video 720p của 3 video tiếng Việt từ máy này. Ghi lại lỗi gặp phải (bot check, PO token, yêu cầu JS runtime như Deno) và cách xử lý (cookies, plugin, phiên bản yt-dlp). Thử thêm một video vừa đăng vài phút để xem đã có bản 720p và phụ đề tự động chưa.
2. Theo dõi RSS của vài kênh tin tức đăng thường xuyên (nhóm không có kênh riêng), poll mỗi 30 giây, ghi độ trễ từ lúc video công khai tới lúc video xuất hiện trong feed.
3. Đo cùng độ trễ đó với endpoint `playlistItems` của YouTube API trên uploads playlist.

Nghiệm thu:

- [x] `docs/spikes/ytdlp-rss.md` có kết quả đo, danh sách phần mềm cần cài thêm cho yt-dlp, và kết luận.
- [x] Nếu RSS trễ quá 3 phút, file ghi rõ màn 3 sẽ dùng nút Check now lúc demo.

Kiểm tra: đọc và duyệt file kết quả.

File: `docs/spikes/ytdlp-rss.md`, `docs/spikes/*.py`.
Người làm: Thi. Phụ thuộc: không có. Cỡ: S.

### T3: Spike môi trường GPU và các model

Kiểm tra bốn thư viện GPU cùng cài được bằng một lần `uv sync` và chạy tuần tự trong cùng một process trên WSL:

- faster-whisper (large-v3, và PhoWhisper nếu chuyển đổi được) với một đoạn audio tiếng Việt 5 phút;
- PaddleOCR (thử bản GPU) với 20 khung hình có chữ tiếng Việt;
- model khớp khuôn mặt (ứng viên InsightFace qua onnxruntime-gpu) với ảnh của thành viên nhóm;
- model embedding ảnh (ứng viên CLIP hoặc DINOv2 qua torch) với vài ảnh mẫu bị cắt, đổi màu.

Ghi lại giấy phép sử dụng của model khuôn mặt và model embedding.

Nghiệm thu:

- [x] `docs/spikes/gpu-models.md` ghi: phiên bản từng thư viện cài được cùng nhau; model được chọn cho từng việc; thời gian xử lý 5 phút audio; thời gian nạp mỗi model; WER của STT trên 1 phút audio gán nhãn tay; OCR có giữ được dấu tiếng Việt không.
- [x] Nếu không cài chung được, file ghi phương án dự phòng đã thử được (PaddleOCR chạy CPU, hoặc tách môi trường cho worker `gpu`). Không áp dụng: bốn thư viện cài chung được bằng một lần uv sync và chạy chung một process (xem mục "Kiểm tra môi trường chung" trong file kết quả).

Kiểm tra: đọc và duyệt file kết quả.

File: `docs/spikes/gpu-models.md`.
Người làm: Bảo. Phụ thuộc: không có. Cỡ: M.

### T4: Hợp đồng C1–C5

Viết mô hình Pydantic cho:

- C1: manifest, kèm enum `status`;
- C2: `Video`, `Channel`, `Transcript`, `Comment`, `Thumbnail`, `MediaFile`, `Normalized`, enum `Cap` và `CollectLevel`;
- C3: `Timeline`, có khối `thumbnails`;
- C4: `EntityHit`, `Finding` (có `triggers`), `ReviewDecision`;
- C5: định dạng `sources.toml`, `ai.toml` (có khả năng `vision`, `structured` cho từng model) và `analysis.toml`.

Lệnh `h4wk schema export` xuất JSON Schema vào `docs/contracts/`. Thi viết; Bảo cùng duyệt C3, C4 và phần `ai.toml` của C5.

Nghiệm thu:

- [x] Mỗi mô hình có trong test ít nhất một ví dụ hợp lệ và một ví dụ bị từ chối.
- [x] `h4wk schema export` sinh đủ file schema cho C1–C5.
- [x] Hai người đã duyệt hợp đồng.

Kiểm tra: `uv run pytest tests/unit/test_contracts.py`.

File: `src/h4wk/{evidence/models.py,collectors/models.py,media/timeline.py,analysis/models.py,core/config_models.py}`, `tests/unit/test_contracts.py`.
Người làm: Thi. Phụ thuộc: T1. Cỡ: M.

### T44: Bản thu mẫu

Dựng tay một bản thu mẫu trong `tests/fixtures/captures/<video_id>/`, theo đúng C1. Bản thu dùng một video ngắn do nhóm tự quay (tối đa 60 giây), cần một thành viên đóng vai đối tượng. Video có:

- lời nói nhắc tên đối tượng giả, kèm từ xúc phạm;
- chữ trên hình nhắc tên đối tượng;
- một đoạn chỉ có ảnh chế khuôn mặt thành viên đóng vai đối tượng, không ai nhắc tên;
- một dòng chữ nhỏ ở góc chỉ hiện 1 giây.

Kèm theo là `normalized.json`, `manifest.json`, `timeline.json`, `hits.json` và `findings.json` mẫu, cùng ảnh khuôn mặt mẫu và ảnh mẫu của đối tượng. Các task của cả hai người dùng bản thu này để làm và test trước khi phần của người kia xong.

Nghiệm thu:

- [x] Mọi file JSON mẫu validate được theo C1–C4.
- [x] `verify` (T5) chạy trên bản thu mẫu báo OK; trước khi có T5, SHA-256 trong manifest được kiểm bằng `sha256sum`.
- [ ] Quay video thật: lời nói tiếng Việt có tên đối tượng giả, khuôn mặt thật của thành viên đóng vai đối tượng. Thay video và ảnh khuôn mặt mẫu trong `tests/fixtures/build_sample_capture.py` rồi chạy lại script. Mục này phải xong trước T18 và T41.

Kiểm tra: `uv run pytest tests/unit/test_fixtures.py`.

Bản hiện tại dùng video tổng hợp do `tests/fixtures/build_sample_capture.py` dựng (chữ và ảnh vẽ bằng ffmpeg, tiếng bíp thay giọng nói, khuôn mặt là hình vẽ). Khi nhóm quay video thật, thay video và ảnh trong script rồi chạy lại để tính lại SHA-256.

File: `tests/fixtures/captures/*`, `tests/fixtures/refs/*`, `tests/unit/test_fixtures.py`.
Người làm: Thi. Phụ thuộc: T4. Cỡ: M.

## Phase 1: Luồng tối giản

### T5: `evidence-store`: ghi bản thu, manifest, verify

`CaptureWriter` mở một thư mục tạm cùng ổ đĩa với `data/` để adapter ghi dữ liệu vào `sources/<provider>/`. Khi gọi `finalize(normalized, source_calls)`, writer ghi `normalized.json`, tính SHA-256 từng file (gồm cả `normalized.json`), ghi `manifest.json`, `rename` thư mục sang `captures/<ts>`, rồi đặt cả file lẫn thư mục ở chế độ chỉ đọc. `verify(capture_dir)` trả về kết quả từng file: OK, FAIL, missing hoặc unexpected. CLI có thêm lệnh `h4wk verify`. Test dọn thư mục tạm bằng hàm mở khoá riêng cho test.

Nghiệm thu:

- [x] Sửa 1 byte thì `verify` báo FAIL đúng file đó.
- [x] Xoá một file thì báo `missing`; thêm một file lạ thì báo `unexpected`.
- [x] Thu lại cùng video thì manifest mới có `previous_capture`.

Kiểm tra: `uv run pytest tests/unit/test_evidence.py`.

File: `src/h4wk/evidence/{writer.py,verify.py}`, `cli.py`, `tests/unit/test_evidence.py`.
Người làm: Thi. Phụ thuộc: T4. Cỡ: M.

### T6: `core`: đối tượng, nhật ký, chỉ mục

SQLite (chế độ WAL, qua SQLModel) làm chỉ mục cho đối tượng, video, bản thu, nghi vấn và job. Module ghi `data/entities.json` và `data/log/audit.jsonl`. Có API liệt kê và thêm đối tượng (tên, biệt danh, viết tắt). Không có khái niệm case (quyết định 2026-11-19). Lệnh dựng lại chỉ mục làm ở T45.

Nghiệm thu:

- [x] Thêm đối tượng qua API thì có `entities.json` và một dòng trong audit.
- [x] Một thao tác thất bại cũng để lại dòng audit với `status` lỗi.
Kiểm tra: `uv run pytest tests/unit/test_cases.py`.

File: `src/h4wk/core/{db.py,entities.py,audit.py}`, `api/entities.py`, tests.
Người làm: Thi. Phụ thuộc: T4. Cỡ: M.

### T7: `core`: đăng nhập 2 tài khoản

Lệnh `h4wk user create` lưu mật khẩu dạng hash (argon2 hoặc bcrypt). Đăng nhập và đăng xuất bằng session cookie. Mọi API trừ `/api/health` và `/api/auth/*` đều yêu cầu đăng nhập. `actor` trong audit lấy từ session theo dạng `user:<username>`. Đăng nhập sai được ghi vào system audit.

Nghiệm thu:

- [x] Gọi API khi chưa đăng nhập nhận về 401.
- [x] Audit ghi đúng `user:<username>`; đăng nhập sai có dòng trong system audit.

Kiểm tra: `uv run pytest tests/unit/test_auth.py`.

File: `src/h4wk/core/auth.py`, `api/auth.py`, `cli.py`, tests.
Người làm: Thi. Phụ thuộc: T6. Cỡ: S.

### T8: `collectors`: hợp đồng adapter và orchestrator

Định nghĩa `Collector` protocol, các loại lỗi `Transient | Blocked | QuotaExceeded | NotFound | Unsupported` và registry.

`Orchestrator.collect(target, level)` xác định các `Cap` cần lấy theo mức thu. Với mỗi `Cap`, orchestrator thử các nguồn đang bật theo thứ tự ưu tiên trong `config/sources.toml`:

- `Transient` thì thử lại 3 lần rồi chuyển nguồn; `Blocked` hoặc `QuotaExceeded` thì chuyển nguồn ngay;
- nguồn lỗi 5 lần liên tiếp (tính cả `Blocked`) bị tạm ngưng 30 phút;
- nguồn bị tắt ghi `disabled`, nguồn đang tạm ngưng ghi `suspended`, không còn nguồn nào thì ghi `no_source`;
- cờ `fault_injection` giả lập một nguồn bị chặn.

Mỗi lần gọi được ghi vào `source_calls`. Orchestrator gộp các phần dữ liệu chung thành một `Normalized` rồi finalize qua `CaptureWriter`.

Kèm theo là hàm phân loại đầu vào: link hoặc ID video, kênh, `@handle`, playlist.

Nghiệm thu:

- [x] Có test với `FakeCollector` cho các trường hợp thành công, chuyển nguồn, hết quota, tạm ngưng nguồn, nguồn bị tắt và không còn nguồn.
- [x] Manifest liệt kê cả những lần gọi thất bại.
- [x] Một adapter giả mới chỉ cần một file và một dòng đăng ký là được orchestrator dùng (có test).

Kiểm tra: `uv run pytest tests/unit/test_orchestrator.py tests/unit/test_target_parse.py`.

File: `src/h4wk/collectors/{base.py,orchestrator.py,registry.py,targets.py}`, tests.
Người làm: Thi. Phụ thuộc: T5. Cỡ: M.

### T9: Adapter yt-dlp

`YtDlpCollector` hỗ trợ các Cap: `VIDEO_METADATA`, `CHANNEL_METADATA`, `CHANNEL_VIDEOS`, `PLAYLIST_VIDEOS`, `TRANSCRIPTS` (phụ đề tiếng Việt, gắn nhãn `uploaded` hoặc `auto`), `COMMENTS` (toàn bộ, kèm reply), `THUMBNAILS` (bản lớn nhất và `0–3.jpg`), `MEDIA` (720p và audio). Chọn định dạng có phương án dự phòng khi chưa có bản 720p. Adapter phân loại lỗi của yt-dlp, ghi phiên bản yt-dlp, và hỗ trợ file cookies cùng các yêu cầu cài đặt mà T2 tìm ra.

Nghiệm thu:

- [x] Phần chuyển sang dữ liệu chung có test dùng `info.json` và file phụ đề đã ghi sẵn, không gọi mạng.
- [x] Test live thu đủ một video thật.

Kiểm tra: `uv run pytest tests/unit/test_ytdlp_normalize.py` và `uv run pytest -m live -k ytdlp`.

File: `src/h4wk/collectors/providers/ytdlp.py`, `tests/fixtures/raw/ytdlp/*`, tests.
Người làm: Thi. Phụ thuộc: T8, T2. Cỡ: M.

### T10: `media`: timeline từ phụ đề YouTube

Chọn transcript chính theo thứ tự `uploaded > stt > auto > supadata_ai` (cấu hình được), gom các câu thành đoạn dài 8–20 giây, rồi ghi `derived/<capture>/timeline.json`. Ở bước này timeline mới có `speech`; `ocr`, `visual` và khối `thumbnails` để trống. Bước này idempotent.

Nghiệm thu:

- [x] Timeline của bản thu mẫu (T44) validate được theo C3.
- [x] Mỗi đoạn dài tối đa 20 giây, trừ trường hợp một câu đơn lẻ đã dài hơn.

Kiểm tra: `uv run pytest tests/unit/test_timeline.py`.

File: `src/h4wk/media/{timeline.py,transcripts.py}`, tests.
Người làm: Bảo. Phụ thuộc: T44. Cỡ: S.

### T11: `analysis`: dấu hiệu tên và tầng tĩnh

Văn bản được chuẩn hoá trước khi so: chuẩn NFC, bỏ dấu, chuyển chữ thường, gộp khoảng trắng. Bộ khớp tìm tên đầy đủ và biệt danh theo ranh giới từ; mỗi từ dài từ 4 ký tự được sai tối đa 1 ký tự, từ ngắn hơn phải khớp chính xác. Viết tắt phải khớp đủ ký tự theo ranh giới từ, không phân biệt hoa thường. Bộ khớp quét `speech`, `ocr`, tiêu đề, mô tả, comment và chữ OCR trên thumbnail, ghi các dấu hiệu tên vào `analysis/<run_id>/hits.json`.

Từ điển ban đầu nằm ở `analysis/lexicon/vi_insults.txt`, chia nhóm theo danh sách thông tin xâm phạm an ninh quốc gia, mỗi nhóm gắn một category của C4. Vùng văn bản có dấu hiệu tên mà có cụm từ trong từ điển thì sinh nghi vấn `analyzer: "static"`, category của nhóm, severity `medium`, ghi vào `findings.json`. Dấu hiệu tên đơn thuần không sinh nghi vấn.

Nghiệm thu, với đối tượng "Nguyễn Văn Hùng", viết tắt "NVH":

- [x] Khớp: "nguyen van hung", "NGUYỄN VĂN HÙNG", "Nguyễn Văn Hùnh" và "Nguyễnn Văn Hùng" (sai 1 ký tự ở từ dài từ 4 ký tự), "NVH".
- [x] Không khớp: "Nguyễn Văn Hà", "Nguyễn Văn Hoàng", "Nguyễn Vn Hùng" (từ ngắn "Văn" bị sai), "NVHA" và "ANVH" (viết tắt dính chữ khác), "Nguyễn Văn" (thiếu từ).
- [x] Giới hạn đã biết, có test ghi nhận: "Nguyễn Văn Hưng" vẫn khớp vì bỏ dấu cho ra cùng một chuỗi.
- [x] Chỉ nhắc tên thì có dấu hiệu trong `hits.json` nhưng không có nghi vấn.

Kiểm tra: `uv run pytest tests/unit/test_static_match.py`.

File: `src/h4wk/analysis/{normalize.py,hits.py,static.py,runner.py,lexicon/}`, tests.
Người làm: Bảo. Phụ thuộc: T4, T6. Cỡ: M.

### T12: `jobs`: luồng collect → media → analyze

Huey dùng một file SQLite riêng làm nơi lưu, với hai hàng đợi: `default` và `gpu` (1 worker). `pipeline.run(target, level, trigger)` chạy lần lượt các bước; mỗi bước cập nhật trạng thái và phần trăm tiến độ vào chỉ mục. Trong lúc chờ T10 và T11, bước media và analyze dùng bản giả đọc từ bản thu mẫu của T44.

Các quy tắc:

- Một video đã có bản thu trong 10 phút trước sẽ không bị thu lại, trừ khi gọi với `force`.
- Mỗi job ghi lại người hoặc quy tắc đã kích hoạt nó.
- Kênh và `@handle` được chuyển cho watchlist ở T30, playlist được xử lý ở T46. Trước khi có các task đó, API trả lỗi rõ ràng.

API gồm `POST /api/collect`, `GET /api/jobs`, `GET /api/jobs/{id}` và `GET /api/findings` (nghi vấn của lần chạy mới nhất cho mỗi bản thu).

Nghiệm thu:

- [x] Integration test chạy toàn luồng với adapter giả và bản thu mẫu, kết thúc với nghi vấn có trong chỉ mục và trả về qua API findings.
- [x] Khi một bước lỗi, job chuyển sang `failed`, có thông báo lỗi và có dòng audit.

Kiểm tra: `uv run pytest tests/integration/test_pipeline.py`; thủ công: chạy hai `huey_consumer` rồi gọi API với một link thật.

File: `src/h4wk/jobs/{queue.py,pipeline.py}`, `api/jobs.py`, `api/findings.py`, tests.
Bước media dùng timeline từ phụ đề của T10, bước analyze dùng tầng tĩnh của T11. Proxy, keyframe, OCR, STT và VLM được nối vào ở T22.

Người làm: Thi. Phụ thuộc: T7, T9, T44. Tích hợp sau: T10, T11. Cỡ: M.

### T13: UI tối giản: login, đối tượng, collect, danh sách nghi vấn

Kiểu TypeScript được sinh từ OpenAPI bằng `npm run gen:api`. Các trang cần có:

- Login.
- Entities: danh sách và thêm đối tượng. Đăng nhập xong vào thẳng Dashboard; không có màn Cases.
- Collect: dán link, chọn mức thu (mặc định `full`), danh sách job với tiến độ poll mỗi 2 giây và thông báo lỗi nếu job thất bại.
- Findings: bảng nghi vấn gồm video, mốc thời gian, trích dẫn và category.

Toàn bộ giao diện viết bằng tiếng Anh.

Nghiệm thu:

- [x] Từ trình duyệt làm trọn được luồng: đăng nhập, thêm đối tượng, dán link, chờ job chạy xong, thấy nghi vấn. (Nghiệm thu 19/11 trên Chrome: đăng nhập, thêm đối tượng "Tô Lâm", dán link `8VB-P9Wk7v4` mức metadata, job xong, nghi vấn `unsupported_accusation` medium hiện ở Findings.)
- [x] Job lỗi hiện thông báo lỗi trên trang Collect. (Nghiệm thu 19/11 trên Chrome: thông báo đỏ `vlm: media.vision: no valid result (Gemini API error)`.)

Kiểm tra: `npm run build && npx tsc --noEmit`, rồi thao tác thủ công đúng luồng trên.

File: `web/src/{api/,pages/Login.tsx,pages/Entities.tsx,pages/Collect.tsx,pages/Findings.tsx}`.
Người làm: Thi. Phụ thuộc: T12. Cỡ: M.

### Checkpoint A (cuối tuần 1)

Gồm các task: T13.

- [x] `uv run pytest` và `npm run build` đều pass.
- [x] Luồng tối giản chạy trọn với 1 video thật, thao tác từ trình duyệt.
- [x] Hai người duyệt lại C1–C5 và chốt hợp đồng. Sau mốc này, mọi thay đổi hợp đồng phải được Thi đồng ý.
- [x] Đã đọc kết quả spike T2 và T3, và cập nhật SPEC nếu cần.

## Phase 2: Nguồn thu, AI và hoàn thiện luồng xử lý

### T14: Adapter YouTube Data API và quota

`YouTubeApiCollector` hỗ trợ `VIDEO_METADATA`, `CHANNEL_METADATA`, `COMMENTS` (commentThreads và replies), `CHANNEL_VIDEOS` (qua uploads playlist), `PLAYLIST_VIDEOS` và `THUMBNAILS` (tải từ URL thumbnail API trả về). Quota được đếm theo ngày, reset lúc nửa đêm giờ Pacific; khi dùng tới 90% thì adapter ném `QuotaExceeded`. Video của kênh lấy qua uploads playlist, không dùng `search.list`.

Nghiệm thu:

- [x] Phần chuyển sang dữ liệu chung có test dùng response đã ghi sẵn.
- [x] Tắt yt-dlp thì metadata, comment và thumbnail vẫn thu được; manifest ghi yt-dlp là `disabled` và `MEDIA` là `no_source`; job vẫn chạy phân tích phần văn bản.

Kiểm tra: `uv run pytest tests/unit/test_ytapi_normalize.py` và `uv run pytest -m live -k ytapi`.

Hạn chế đã biết: comment lấy toàn bộ (SPEC 10.3), không giới hạn; khoảng 1 đơn vị quota cho 100 comment, nên video rất nhiều comment tốn nhiều quota. Chạm ngưỡng 90% giữa chừng thì phần comment đã lấy bị bỏ và orchestrator chuyển sang yt-dlp. Người dùng đã chấp nhận cho demo (2026-11-19).

File: `collectors/providers/youtube_api.py`, `collectors/quota.py`, fixtures, tests.
Người làm: Thi. Phụ thuộc: T8. Cỡ: M.

### T15: Adapter Supadata và credit

`SupadataCollector` hỗ trợ `TRANSCRIPTS` và `VIDEO_METADATA`. Transcript do AI của Supadata tạo được gắn nhãn `supadata_ai`. Với transcript lấy từ phụ đề YouTube, nhãn lấy theo thông tin Supadata trả về; nếu API không cho biết là `uploaded` hay `auto` thì gắn `supadata_ai` và ghi chú lại. Credit được đếm theo tháng.

Nghiệm thu:

- [x] Phần chuyển sang dữ liệu chung có test dùng response đã ghi sẵn.
- [x] Khi bật `fault_injection` cho yt-dlp, Supadata được gọi thay để lấy transcript, và manifest ghi đủ cả hai lần gọi.

Kiểm tra: `uv run pytest tests/unit/test_supadata.py tests/unit/test_orchestrator.py`.

Ghi chú: Supadata không cho biết phụ đề YouTube là uploaded hay auto, nên mọi transcript từ Supadata gắn supadata_ai. Không có phụ đề tiếng Việt thì gọi mode generate (AI, 2 credit/phút, chờ job tối đa 10 phút). Credit trong kỳ lấy từ GET /me của Supadata (nhớ 5 phút), không tự đếm; người dùng chốt 2026-11-19.

File: `collectors/providers/supadata.py`, fixtures, tests.
Người làm: Thi. Phụ thuộc: T8. Cỡ: S.

### T45: `core`: dựng lại database chỉ mục

`h4wk reindex` xoá chỉ mục cũ rồi dựng lại từ `data/`: đối tượng, video, bản thu, nghi vấn của lần chạy mới nhất, và quyết định rà soát trong `reviews.jsonl`. Tài khoản, watchlist và lịch sử job không được dựng lại; đây là hạn chế đã chấp nhận ở SPEC 10.1.

Nghiệm thu:

- [x] Xoá `index.db` rồi chạy `reindex` thì API trả về đối tượng, video và nghi vấn như trước.
- [x] Quyết định rà soát trong một `reviews.jsonl` mẫu được nạp lại đúng.

Ghi chú: reindex nạp nghi vấn của mọi lần chạy (API vẫn chỉ hiện lần mới nhất) và xoá cả `index.db` theo quyết định của người dùng.

Kiểm tra: `uv run pytest tests/integration/test_reindex.py`.

File: `src/h4wk/core/reindex.py`, `cli.py`, `tests/integration/test_reindex.py`.
Người làm: Thi. Phụ thuộc: T6, T44. Cỡ: S.

### T46: `jobs`: chạy lại job bị treo và xử lý playlist

Khi worker khởi động, job đang ở trạng thái `running` được đưa lại vào hàng đợi; nhờ các bước idempotent, job chạy tiếp từ bước dở dang. Link playlist được tách thành các job, mỗi video một job, tối đa 50 video (cấu hình được).

Nghiệm thu:

- [x] Integration test tắt worker giữa chừng rồi bật lại; job chạy tiếp tới `done` và không làm lại bước đã xong.
- [x] Dán link một playlist có 3 video (dùng adapter giả) thì tạo đúng 3 job.

Ghi chú: playlist không lưu bản thu (người dùng quyết); `POST /api/collect` trả `list[Job]`; mỗi hàng đợi chỉ nhận lại bước của mình khi khởi động. Giao diện đã đồng bộ: `collect()` trả `Job[]`, schema đã sinh lại.

Kiểm tra: `uv run pytest tests/integration/test_recovery.py tests/integration/test_playlist.py`.

File: `src/h4wk/jobs/{recovery.py,pipeline.py}`, tests.
Người làm: Thi. Phụ thuộc: T12. Cỡ: S.

### T16: `ai-gateway`: lõi

Gateway có hai hàm `complete_structured(task, messages, schema)` và `describe_image(task, image, prompt, schema)`. Mỗi tác vụ AI được định tuyến tới danh sách `(provider, model)` trong `config/ai.toml` theo C5. Cấu hình gán `media.vision` cho model không có khả năng `vision` bị từ chối khi nạp. Đầu ra qua Pydantic validate; sai thì gửi lại kèm thông báo lỗi tối đa 2 lần, sau đó chuyển nhà cung cấp. Số request đồng thời được giới hạn theo nhà cung cấp. Mỗi lần gọi ghi vào `data/ai_calls.jsonl`. Có `FakeProvider` dùng cho test.

Nghiệm thu:

- [x] Có test cho các trường hợp: JSON sai được sửa ở lần gửi lại; nhà cung cấp 1 lỗi thì chuyển sang nhà cung cấp 2; định tuyến đọc đúng từ cấu hình; gán `media.vision` cho model không có `vision` thì báo lỗi.

Kiểm tra: `uv run pytest tests/unit/test_ai_gateway.py`.

File: `src/h4wk/ai/{gateway.py,base.py,config.py,fake.py}`, tests.
Người làm: Bảo. Phụ thuộc: T1, T4. Cỡ: M.

### T17: `ai-gateway`: provider anthropic, openai_compat, gemini

Viết ba adapter. Mỗi adapter dùng tool calling hoặc JSON schema khi model có khả năng `structured`, nếu không thì dùng JSON mode, và gửi được ảnh với model có `vision`. `openai_compat` nhận `base_url`. File `config/ai.toml.example` có sẵn mục cho Anthropic, OpenAI, Gemini, DeepSeek, Qwen (DashScope), GLM, Kimi và OpenRouter, mỗi model ghi rõ khả năng.

Trước khi viết adapter Anthropic, đọc skill `claude-api`. Với các nhà cung cấp khác, lấy tên model, khả năng đọc ảnh và cách bật đầu ra có cấu trúc từ tài liệu chính thức; kiểm tra cả giới hạn JSON Schema của từng nhà (ví dụ `anyOf`, `$ref`).

Nghiệm thu:

- [x] Mỗi nhà cung cấp đã có key chạy được một lời gọi văn bản trong `-m live`, trả về đối tượng hợp lệ.
- [x] Mỗi nhà cung cấp có model đọc ảnh chạy được một lời gọi ảnh.

Đã triển khai ba adapter và kiểm thử qua SDK. Nghiệm thu live ngày 20/11: gemini (`gemini-3.6-flash`) và openrouter qua `openai_compat` (`nvidia/nemotron-3.5-super-vl:free`) qua cả lời gọi văn bản lẫn ảnh (4 passed). Anthropic bị bỏ qua vì chưa có key; có key thì chạy lại lệnh dưới.

Kiểm tra: `uv run pytest -m live -k ai_provider`.

File: `src/h4wk/ai/providers/{anthropic.py,openai_compat.py,gemini.py}`, `config/ai.toml.example`, tests.
Người làm: Bảo. Phụ thuộc: T16. Cỡ: M.

### Checkpoint B

- [x] Có test chứng minh việc chuyển nguồn thu khi lỗi.
- [x] Đổi nhà cung cấp của một tác vụ AI trong `ai.toml` mà không sửa code, và lời gọi live vẫn chạy.

Ghi chú 20/11: chuyển nguồn thu có `test_fault_injection_ytdlp_falls_back_to_supadata` trong `tests/unit/test_orchestrator.py`. Đổi tuyến `analysis.classify` trong `ai.toml` giữa gemini và openrouter rồi gọi `AIGateway.complete_structured` thật: cả hai lần trả về đối tượng hợp lệ, và `ai_calls.jsonl` ghi đúng nhà cung cấp đã chọn.

## Phase 3: Media đa phương thức

### T18: Proxy 480p, audio, STT

ffmpeg tạo `proxy_480p.mp4` (H.264) và `audio_16k.wav` (mono). faster-whisper, với model chọn ở T3, tạo `transcripts/stt.vi.json` có mốc thời gian theo đoạn; ở mức thu `full`, bước này luôn chạy. Các bước GPU chạy trên hàng đợi `gpu`, model được nạp một lần cho mỗi worker. Mỗi bước idempotent.

Nghiệm thu:

- [ ] Video mẫu (T44) cho ra transcript có mốc thời gian hợp lệ.
- [x] Với video không có phụ đề, timeline dùng transcript `stt`.
- [x] Chạy hai job cho hai bản thu riêng trong cùng worker chỉ nạp Whisper large-v3 một lần (kiểm qua log).

Đã kiểm tra bằng FFmpeg thật việc tạo proxy và audio, khôi phục tệp bị cắt dở và giữ OCR khi chạy lại. Test với model mô phỏng kiểm tra thứ tự phụ đề và log nạp model cho hai bản thu. Worker của hàng đợi GPU dùng chung một `SttWorker` giữa các job. Kiểm thử API trên T44 tổng hợp xác nhận một lần nạp Whisper thật trên RTX 3050. Chạy lại bằng `uv run --extra stt pytest -m gpu tests/integration/test_pipeline.py` với `H4WK_STT_MODEL` trỏ tới model cục bộ.

Kiểm tra: `uv run pytest tests/integration/test_media_stt.py`, cần `ffmpeg` và `ffprobe` trong PATH. Để nghiệm thu GPU, đặt `H4WK_STT_MODEL` thành tên hoặc đường dẫn model đã chọn và `H4WK_T44_CAPTURE` thành thư mục bản thu T44 rồi chạy `uv run --extra stt pytest -m gpu tests/integration/test_media_stt.py`.

File: `src/h4wk/media/{proxy.py,stt.py,models.py}`, tests.
Người làm: Bảo. Phụ thuộc: T3, T10, T44 (video thật; STT không chạy được trên tiếng bíp của bản tổng hợp). Cỡ: M.

### T19: Keyframe theo mức thay đổi

PySceneDetect tách cảnh và lấy một khung đại diện cho mỗi cảnh. Trong mỗi cảnh, video được giải mã 2 khung mỗi giây ở độ phân giải nhỏ. Khung được giữ khi pHash toàn khung hoặc độ khác biệt trung bình của một ô bất kỳ trong lưới 4×4 vượt ngưỡng (cấu hình được), so với khung giữ gần nhất. Kết quả ghi vào `frames/NNNNNN.jpg` và `frames/index.json` (t, scene, hash).

Nghiệm thu:

- [x] Clip thử có một dòng chữ nhỏ ở góc chỉ hiện 1 giây thì khung đó được giữ.
- [x] Cảnh tĩnh 2 phút cho ra tối đa 3 khung.

Kiểm tra: `uv run pytest tests/unit/test_keyframes.py`, dùng các clip thử tự tạo bằng ffmpeg.

File: `src/h4wk/media/keyframes.py`, `tests/fixtures/clips/*`, tests.
Người làm: Bảo. Phụ thuộc: T18. Cỡ: M.

### T20: OCR trên keyframe và thumbnail

PaddleOCR tiếng Việt chạy trên từng keyframe và thumbnail, ghi `ocr.json` gồm frame, t, text, bbox và score.

Nghiệm thu:

- [x] Khung mẫu có chữ "LỪA ĐẢO" cho ra đúng chữ đó, giữ nguyên dấu, kèm bbox.

Gọi `process_ocr(capture_dir, derived_dir)` để đọc chỉ mục T19 và thumbnail cục bộ. Trong `derived/<capture>/ocr.json`, mỗi dòng ở `lines` có `frame`, `t` (giây; null với thumbnail), `text`, `bbox` theo thứ tự x, y, rộng, cao (pixel ảnh nguồn) và `score`. Mục `images` liệt kê cả ảnh không có chữ.

Worker CPU dùng môi trường uv riêng để giữ đúng phiên bản OpenCV của T19. Lần đầu cần mạng để tải dependency và trọng số. Bộ phát hiện là [PP-OCRv5 mobile của PaddlePaddle](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det). Bản demo dùng bộ nhận dạng tiếng Việt của meomeo163, phát hành theo CC BY-NC 4.0. [Model card và điều kiện sử dụng](https://huggingface.co/meomeo163/PP-OCRv5-vi-latin-rec-v4)

Kiểm tra cả inference CPU thật: `H4WK_TEST_OCR=1 uv run pytest tests/unit/test_ocr.py` trong `backend/`.

File: `src/h4wk/media/ocr.py`, tests.
Người làm: Bảo. Phụ thuộc: T19. Cỡ: S.

### T21: VLM mô tả keyframe và thumbnail

Gọi `gateway.describe_image("media.vision", …)` cho từng keyframe và thumbnail, chạy song song có giới hạn. Đầu ra gồm mô tả và danh sách `offensive_cues` (ảnh ghép, còng tay, vẽ sừng, chữ chửi…). Prompt cấm VLM đoán danh tính người trong ảnh. Kết quả ghi vào `vision.json` kèm nhà cung cấp và model.

Nghiệm thu:

- [x] Test với `FakeProvider` cho ra `vision.json` hợp lệ (trong `tests/integration/test_pipeline.py`).
- [ ] Test live với 3 khung mẫu đã biết trước dấu hiệu (một ảnh ghép còng tay, một ảnh có chữ chửi, một ảnh bình thường): hai khung đầu có `offensive_cues` đúng loại, khung thứ ba không có.

Kiểm tra tích hợp với nhà cung cấp giả bằng `uv run pytest tests/integration/test_pipeline.py -k full_flow`. Từ 21/11, test live dùng Ollama `qwen3-vl:4b` (T52), không cần API key.

File: `src/h4wk/media/vision.py`, `media/prompts/vision.md`, tests.
Người làm: Bảo. Phụ thuộc: T17, T19. Cỡ: S.

### T22: Timeline đầy đủ

Kết quả OCR và VLM được gắn vào đoạn theo thời gian `t` của khung; kết quả trên thumbnail được ghi vào khối `thumbnails`. Timeline ghi thêm `source_video_sha256` lấy từ manifest. Các bước T18–T21 được nối vào luồng `jobs` theo đúng mức thu, mỗi bước có tiến độ riêng. Task này sửa `jobs/pipeline.py` của Thi, nên hai người cần phối hợp.

Nghiệm thu:

- [x] Timeline T44 tổng hợp có đủ speech, ocr, visual và khối thumbnails, và validate được theo C3 trong kiểm thử API. STT, nhận dạng OCR và nhà cung cấp VLM được mô phỏng trong kiểm thử này.
- [x] Màn Collect hiện đủ các bước collect → transcribe → frames → OCR/VLM → analyze.

Kiểm tra: `uv run pytest tests/integration/test_pipeline.py`.

File: `media/timeline.py`, `jobs/pipeline.py`, tests.
Người làm: Bảo. Phụ thuộc: T20, T21, T12, T13. Cỡ: S.

### Checkpoint C

- [ ] Đo màn 2 với video 5 phút trên máy demo, ghi vào `docs/spikes/latency.md`, gồm cả thời gian nạp model.
- [ ] Mở `timeline.json` của 3 video thật và kiểm tra: đoạn có đúng mốc thời gian, chữ OCR đọc đúng, `offensive_cues` khớp với hình.

## Phase 4: Phân tích và rà soát

### T23: `analysis`: tầng LLM

Tầng LLM gửi tới tác vụ AI `analysis.classify` các phần sau:

- đoạn có dấu hiệu (tên ở T11; khuôn mặt và ảnh mẫu khi T40, T41 xong), kèm một đoạn trước và một đoạn sau làm ngữ cảnh;
- trong video liên quan tới đối tượng, mọi đoạn có `offensive_cues`, kể cả khi không nhắc tên, kèm ngữ cảnh cấp video (tiêu đề, mô tả, danh sách dấu hiệu);
- tiêu đề, mô tả và thumbnail có dấu hiệu hoặc có `offensive_cues`.

Đầu ra theo C4, có `triggers` ghi rõ dấu hiệu nào khiến đoạn được gửi đi. Nghi vấn `visual` phải trích khung hình và nêu lý do dựa trên nội dung hình. Prompt nằm ở `analysis/prompts/classify.md` và phân biệt rõ phê bình hợp lý với bôi nhọ.

Nghiệm thu:

- [x] Đầu ra sai schema không bao giờ được ghi vào `findings.json`.
- [x] Trên bản thu mẫu, LLM thật sinh được ít nhất một nghi vấn từ speech, một từ ocr và một từ visual.
- [x] Đoạn chỉ có ảnh chế, không ai nhắc tên, vẫn được gửi đi nhờ ngữ cảnh cấp video và sinh nghi vấn `visual`.

Quyết định của người dùng: (1) không gọi được LLM thì giữ nghi vấn tĩnh, job vẫn `done`, sự kiện và audit ghi `llm_error`; (2) kết luận `neutral` hoặc `legitimate_criticism` chỉ ghi vào `llm.json`, không vào `findings.json`; (3) LLM kết luận vi phạm cho một mục thì bỏ nghi vấn tĩnh của đúng mục đó và đúng đối tượng đó (mục + đối tượng; thumbnail tính theo từng file).

Kiểm tra: `uv run pytest tests/unit/test_analysis_llm.py` (dùng `FakeProvider`) và `uv run pytest -m live -k analysis`.

File: `src/h4wk/analysis/{llm.py,prompts/classify.md,runner.py}`, tests.
Người làm: Bảo. Phụ thuộc: T11, T16, T22. Cỡ: M.

### T24: `analysis`: comment

Comment và reply có dấu hiệu tên (từ T11) được gửi tới tác vụ AI `analysis.classify_comment` theo lô 20–50 comment, sinh nghi vấn có `source_kind: "comment"` và `comment_id`. Số comment tối đa phân tích cho mỗi video có thể giới hạn bằng `analysis.toml`.

Nghiệm thu:

- [x] Một video có 500 comment chạy xong với số lời gọi LLM không quá ⌈số comment có dấu hiệu / kích thước lô⌉.
- [x] `comment_id` của nghi vấn trỏ đúng tới comment.

Kiểm tra: `uv run pytest tests/unit/test_analysis_comments.py`.

File: `analysis/{comments.py,prompts/classify_comment.md}`, tests.
Người làm: Bảo. Phụ thuộc: T23. Cỡ: S.

### T25: `review`: backend hàng đợi và quyết định

API hàng đợi chỉ trả nghi vấn của lần chạy mới nhất cho mỗi bản thu, lọc được theo video, `source_kind` và trạng thái, sắp theo severity rồi đến thời gian. `POST /api/findings/{id}/decision` nhận status `confirmed`, `rejected` hoặc `needs_info`; `rejected` bắt buộc có note. Mỗi quyết định được ghi thêm vào `reviews.jsonl` theo `finding_id` và `run_id`, ghi audit, rồi cập nhật chỉ mục. Ngoài endpoint này, code không đặt trạng thái `confirmed` ở đâu khác. Task làm và test bằng nghi vấn mẫu của T44.

Nghiệm thu:

- [x] Bác nghi vấn mà không có lý do thì nhận 422.
- [x] Sau `reindex`, trạng thái rà soát vẫn giữ nguyên.
- [x] Chạy phân tích lại thì nghi vấn của lần chạy mới ở trạng thái chưa rà soát; quyết định của lần chạy trước vẫn còn trong `reviews.jsonl`.

Kiểm tra: `uv run pytest tests/unit/test_review.py`.

API: `GET /api/review/queue?video=&source_kind=&status=` trả `{finding, status, video: {id, title, channel}, decisions[]}`; `POST /api/findings/{id}/decision`; `GET /api/findings/{id}/decisions` (mới nhất trước). Giữ trạng thái sau `reindex` đã làm ở T45. Tham số `latest_only=true` (queue, findings, videos, dashboard) chỉ giữ bản thu mới nhất mỗi video.

File: `src/h4wk/review/{queue.py,decisions.py}`, `api/review.py`, tests.
Người làm: Thi. Phụ thuộc: T12, T44, T45. Tích hợp sau: T11, T23. Cỡ: S.

### T26: UI Video detail: trình phát, transcript, thanh thời gian

Backend có endpoint stream bản proxy, hỗ trợ Range. Trang Video detail có trình phát `<video>`, transcript tự cuộn theo thời gian phát kèm dropdown chọn loại transcript để xem, và thanh thời gian tô màu các đoạn có nghi vấn theo severity. Mở trang với `?t=` hoặc `?finding=` thì video phát từ `start − 2s`.

Nghiệm thu:

- [x] Bấm một nghi vấn trong bảng thì video nhảy đúng tới vị trí đó và đoạn tương ứng được tô sáng.

Kiểm tra: `npm run build`, rồi kiểm tra thủ công trên 2 video.

Backend đọc video đã có ở `api/videos.py` (Thi làm trước để giao diện nối): `GET /api/videos`, `/api/videos/{id}`, `/timeline`, `/transcripts`, `/comments`, `/media` (proxy hoặc file gốc, hỗ trợ Range), `/frames/{file}`.

File: `api/media.py`, `web/src/pages/VideoDetail.tsx`, `web/src/components/{Player,TranscriptPane,FindingTimeline}.tsx`.
Người làm: Bảo. Phụ thuộc: T13, T22, T25. Cỡ: M.

### T27: UI Video detail: dải khung hình, comment, lịch sử bản thu

Trang có dải keyframe; bấm vào một khung thì video seek tới thời điểm đó, ảnh lớn hiện ra với khung bao của chữ OCR, khuôn mặt và ảnh mẫu đã khớp, cùng mô tả VLM bên cạnh. Tab Comments đánh dấu các comment bị gắn cờ. Tab Captures liệt kê các lần thu, dùng API của T29.

Nghiệm thu:

- [x] Nghi vấn từ OCR hiện đúng khung hình kèm khung bao.
- [x] Nghi vấn từ comment mở đúng comment.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/components/{FrameStrip,FrameViewer,CommentsTab,CapturesTab}.tsx`, `api/media.py`.
Người làm: Bảo. Phụ thuộc: T26, T29, T24. Tích hợp sau: T40, T41. Cỡ: M.

### T28: UI Review queue

Trang hiển thị danh sách nghi vấn với các bộ lọc. Panel bên cạnh hiện trích dẫn, khung hình, lý do, `triggers`, analyzer, model và liên kết mở trang Video detail tại đúng đoạn. Các nút Confirm, Reject (bắt buộc nhập lý do) và Needs info có phím tắt.

Nghiệm thu:

- [x] Duyệt 10 nghi vấn liên tiếp mà không phải rời trang.
- [x] Mỗi quyết định có một dòng tương ứng trong audit.

Ghi chú: panel hiện khung hình kèm khung bao cho nghi vấn ocr/visual/thumbnail (dùng lại `FrameImage`). 19/11: quyết định bằng phím tắt và dòng audit `review.decide` đã kiểm với 1 nghi vấn. 20/11: duyệt 10 nghi vấn liên tiếp bằng phím `c`/`r`/`n` trên trình duyệt (bản sao dữ liệu), không rời trang, được 10 dòng ở `reviews.jsonl` và 10 dòng `review.decide` ở audit.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/ReviewQueue.tsx`, `web/src/components/FindingPanel.tsx`.
Người làm: Thi. Phụ thuộc: T25, T13. Tích hợp sau: T26. Cỡ: M.

### T29: UI Evidence và Verify integrity

Backend có API liệt kê các bản thu của một video. Trang Capture hiển thị manifest, danh sách file kèm SHA-256 và dung lượng, các nguồn đã gọi cùng trạng thái, và nút tải file gốc. Nút Verify integrity gọi `verify` rồi hiện OK, FAIL, missing hoặc unexpected cho từng file.

Nghiệm thu:

- [x] Sửa 1 byte trên đĩa thì giao diện báo FAIL đúng file đó. (Nghiệm thu 19/11 trên Chrome: sửa 1 bit trong `sources/youtube_api/UCPK…channel.json` thì giao diện báo FAIL đúng file kèm SHA thực tế; đã khôi phục, `h4wk verify` OK.)

Kiểm tra: `npm run build`; thủ công: sửa 1 byte rồi bấm Verify integrity.

Backend xong: `GET /api/videos/{id}/captures/{capture}` (manifest và file), `POST …/verify` (OK, FAIL, missing, unexpected kèm SHA-256 mong đợi và thực tế, có audit), `GET …/files/{path}` (chỉ file có trong manifest). Có test sửa 1 byte. Phần giao diện do phiên UI làm.

File: `api/captures.py`, `web/src/pages/Capture.tsx`.
Người làm: Thi. Phụ thuộc: T5, T13. Cỡ: S.

### T39: Đối tượng và ảnh mẫu

Backend cho tải lên, xem và xoá ảnh mẫu của từng đối tượng, gồm hai loại: ảnh khuôn mặt và ảnh hay bị dùng lại (chân dung quen thuộc, logo). Ảnh lưu ở `data/entities/<entity_id>/refs/{face,image}/`. Trang Entities cho sửa tên, biệt danh, viết tắt và quản lý ảnh mẫu.

Nghiệm thu:

- [x] Tải ảnh lên thì file nằm đúng thư mục và có dòng audit.
- [x] Trang Entities hiện ảnh mẫu theo hai nhóm. (Nghiệm thu 19/11 trên Chrome: Face images và Reused images hiện đúng ảnh; ảnh thử tải lên qua API vì công cụ trình duyệt không chọn được file.)

Kiểm tra: `uv run pytest tests/unit/test_entities.py`, `npm run build` và kiểm tra thủ công.

Backend xong: `PATCH /api/entities/{id}`, `GET /api/entities/{id}/refs`, `POST /api/entities/{id}/refs/{face|image}` (thân request là bytes ảnh JPEG/PNG/WebP, tối đa 10 MB, tên file theo SHA-256), `GET`/`DELETE` từng ảnh; `GET /api/entities` có `ref_counts`. Phần giao diện do phiên UI làm.

File: `src/h4wk/core/entities.py`, `api/entities.py`, `web/src/pages/Entities.tsx`, tests.
Người làm: Thi. Phụ thuộc: T6, T13. Cỡ: M.

### T40: `analysis`: khớp ảnh mẫu

Model embedding chọn ở T3 tính embedding cho ảnh mẫu loại `image`, cho từng keyframe, thumbnail và các ô cắt theo lưới (ví dụ 2×2 và 3×3). Ô hoặc khung có độ tương đồng vượt ngưỡng (cấu hình được) sinh dấu hiệu `via: ref_image` có frame, bbox của ô và điểm số. Dấu hiệu này được tầng LLM của T23 dùng như các dấu hiệu khác.

Nghiệm thu:

- [x] Ảnh mẫu bị cắt một nửa, đổi màu hoặc ghép vào góc khung vẫn khớp trong clip thử.
- [x] Clip không chứa ảnh mẫu không sinh dấu hiệu nào.

Ghi chú: 20/11: bước `match` chạy trên hàng đợi gpu sau VLM, cần extra `match` (thiếu torch thì bỏ qua và ghi audit `media.match`). Ngưỡng mặc định 0,75, đo bằng `uv run --extra match pytest -m live tests/live/test_refimages_live.py -s`: khớp 0,834 (cắt nửa) đến 0,971 (đổi hue), khung T44 có ảnh mẫu 0,898; không khớp 0,486 và 0,549. Mới có hai khung âm tính nên cần kiểm lại trên video thật.

Kiểm tra: `uv run pytest tests/unit/test_refimages.py`.

File: `src/h4wk/analysis/refimages.py`, `tests/fixtures/refs/*`, tests.
Người làm: Bảo. Phụ thuộc: T39, T19, T23. Cỡ: M.

### T41: `analysis`: khớp khuôn mặt

OpenCV YuNet và SFace chạy cục bộ trên CPU trong bước xử lý media, phát hiện khuôn mặt trong keyframe và thumbnail rồi so với ảnh khuôn mặt mẫu của các đối tượng. Khuôn mặt khớp sinh dấu hiệu `via: face` có frame, bbox và điểm số. Đặc trưng của khuôn mặt không khớp chỉ nằm trong bộ nhớ và không được ghi ra đĩa. Tính năng có thể tắt bằng `analysis.toml`.

Nghiệm thu:

- [ ] Trên bản thu mẫu, đoạn ảnh chế khuôn mặt thành viên nhóm sinh dấu hiệu `face`.
- [x] Khuôn mặt của người khác trong clip thử không sinh dấu hiệu, và không có file nào chứa đặc trưng của họ.
- [x] Tắt tính năng trong `analysis.toml` thì bước này bị bỏ qua.

Kiểm tra: `uv run pytest tests/unit/test_faces.py` (đánh dấu `gpu` nếu cần).

File: `src/h4wk/analysis/faces.py`, `tests/fixtures/faces/*`, tests.
Người làm: Bảo. Phụ thuộc: T39, T19, T3, T23, T44 (video thật; bộ dò khuôn mặt không nhận ra hình vẽ của bản tổng hợp). Cỡ: M.

### T42: Checklist demo

Viết `docs/demo-checklist.md` gồm bước chuẩn bị máy (khởi động API, hai worker, frontend), các bước của 3 màn demo và kết quả mong đợi ở mỗi bước. Checklist được chạy cuối mỗi tuần từ tuần 3 và cập nhật khi có tính năng mới.

Nghiệm thu:

- [x] Một người không viết checklist làm theo được từ đầu đến cuối. (20/11: reviewer chạy theo checklist: lệnh khởi động, health, verify trên bản sao đủ 4 trường hợp, đối chiếu nhãn giao diện với code; các bước bấm UI chạy lại ở lần diễn tập T37)

Kiểm tra: Bảo đọc và chạy thử checklist do Thi viết.

File: `docs/demo-checklist.md`.
Người làm: Thi. Phụ thuộc: T13. Cỡ: S.

### Checkpoint D

- [ ] Chạy màn 1 với 3–5 video thật: có ít nhất một nghi vấn speech, một ocr, một visual; video nhảy đúng đoạn; duyệt được nghi vấn.
- [ ] Đo lại màn 2 và ghi vào `docs/spikes/latency.md`.
- [ ] Hai người đọc lại code frontend do agent sinh ra.

## Phase 5: Watchlist

### T30: `watchlist` backend: RSS, Check now, sự kiện

Mỗi mục watchlist là một kênh, có bật/tắt và mức thu riêng (mặc định `full`), quản lý qua CRUD. Khi thêm một kênh, từ API watchlist hoặc khi dán link kênh, `@handle` ở màn Collect:

1. tạo bản thu hồ sơ kênh trong `channels/<channel_id>/captures/`;
2. tạo job cho 10 video mới nhất (cấu hình được);
3. đánh dấu mọi video đang có trong RSS là đã biết.

Một periodic task chạy mỗi 2 phút (cấu hình được), đọc RSS của các kênh đang bật và so với danh sách video đã biết. Gặp video mới thì task tạo job với trigger `system:watchlist:<id>` và ghi sự kiện `new_video`. `POST /api/watchlist/{id}/check` kiểm tra ngay, dùng cả RSS lẫn uploads playlist của YouTube API. Một API khác trả về danh sách sự kiện.

Nghiệm thu:

- [x] Thêm kênh có 15 video trong RSS giả thì tạo đúng 10 job; lần poll tiếp theo không tạo job nào.
- [x] Feed RSS giả thêm 1 entry thì tạo đúng 1 job; chạy lại không tạo job trùng.
- [ ] Thủ công: một kênh tin tức trong watchlist đăng video mới thì video được tự thu và xử lý (bấm Check now nếu chưa thấy).

Kiểm tra: `uv run pytest tests/unit/test_watchlist.py` và làm thủ công màn 3.

Backend xong khi chưa có T14: Check now dùng RSS cộng danh sách video của kênh lấy qua orchestrator (`channel.videos`, hiện là yt-dlp; khi T14 xong thì đặt `youtube_api` lên đầu trong `priority`). API: `GET/POST /api/watchlist`, `PATCH/DELETE /api/watchlist/{id}`, `POST /api/watchlist/{id}/check`, `GET /api/events`. Pipeline ghi thêm sự kiện `job_done`, `job_failed`.

File: `src/h4wk/watchlist/{rss.py,service.py,tasks.py}`, `api/watchlist.py`, tests.
Người làm: Thi. Phụ thuộc: T12, T14. Cỡ: M.

### T31: UI Watchlist và dòng sự kiện

Trang Watchlist cho thêm kênh, bật/tắt, chọn mức thu, bấm Check now và xem thời điểm kiểm tra gần nhất. Task tạo trang Dashboard ở dạng khung, chứa component dòng sự kiện (poll mỗi 5 giây) hiện `New video detected on <channel>` cùng trạng thái job đi kèm. Các số liệu khác của dashboard làm ở T35.

Nghiệm thu:

- [x] Làm trọn màn 3 chỉ bằng giao diện, và thấy sự kiện trên dashboard.

Ghi chú: 19/11: Check now và poll RSS chạy (BBC có 1 video mới, sự kiện `new upload` hiện trên dashboard). 20/11: thêm `@VTV24` mức `metadata` bằng giao diện, 10 job thu ban đầu xong, Collected = 10, 10 sự kiện `job_done` hiện trên Dashboard; Check now báo "No new videos"; bật/tắt, đổi level, xoá kênh đều lưu đúng. Chưa thấy `New video detected` vì kênh không có video mới lúc thử. Lưu ý: bước `media` của job `metadata` cũng xếp trên hàng GPU, nên cần worker GPU chạy.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/Watchlist.tsx`, `web/src/pages/Dashboard.tsx`, `web/src/components/EventFeed.tsx`.
Người làm: Thi. Phụ thuộc: T30, T13. Cỡ: S.

### Checkpoint E (cuối tuần 4)

- [ ] Ba màn demo chạy trọn trên máy demo.
- [ ] Đo màn 3 theo cả hai cách (chờ poll tự động và bấm Check now), ghi vào `docs/spikes/latency.md`.

## Phase 6: Settings và dashboard

### T32: Backend settings và lưu secret

API đọc và ghi cấu hình nguồn thu (bật/tắt, thứ tự ưu tiên theo từng `Cap`) và cấu hình AI (nhà cung cấp, model, định tuyến theo tác vụ AI) theo C5; thay đổi được ghi đè lên file toml. Secret lưu trong `data/secrets.json` với quyền 0600, và API chỉ trả về giá trị đã che (`sk-…abcd`). Có thêm `POST /api/settings/sources/{name}/test` và `/api/settings/ai/{provider}/test`. API trả về trạng thái quota, credit, trạng thái tạm ngưng của từng nguồn, và danh sách `Cap` không còn nguồn nào đang bật. Phần AI làm theo định dạng C5; nút test AI được nối vào gateway khi T16, T17 xong.

Nghiệm thu:

- [x] Không response API nào chứa secret đầy đủ; có test quét toàn bộ response.
- [x] Đổi thứ tự ưu tiên thì job sau dùng thứ tự mới.
- [x] Tắt mọi nguồn có `MEDIA` thì API báo `MEDIA` không còn nguồn.

Kiểm tra: `uv run pytest tests/unit/test_settings.py`.

Đã làm khi chưa có T14, T15: nguồn chưa có adapter trả `implemented: false`, `usage: null`, nút test trả "not implemented yet". Ghi cấu hình là ghi đè cả file toml (mất comment của file mẫu). Secret đặt từ Settings thắng `.env`. Thư mục cấu hình đổi được bằng `H4WK_CONFIG_DIR`, test dùng thư mục riêng. Chỉ mục cũ tự thêm cột mới (cho phép NULL) khi khởi động.

File: `src/h4wk/core/{secrets.py,settings.py}`, `api/settings.py`, tests.
Người làm: Thi. Phụ thuộc: T8, T14, T15. Tích hợp sau: T16, T17. Cỡ: M.

### T33: UI Settings → Sources

Trang làm mục 1–5 của Settings (SPEC 10.10): bật/tắt nguồn, ô nhập key (giá trị bị che), kéo thả thứ tự nguồn trong từng loại dữ liệu kèm cảnh báo khi một loại dữ liệu không còn nguồn, nút Test connection, badge trạng thái và quota hoặc credit đã dùng.

Nghiệm thu:

- [x] Tắt yt-dlp trên giao diện rồi thu một video thì manifest ghi yt-dlp là `disabled`. (Nghiệm thu 19/11 trên Chrome: tắt yt-dlp trên giao diện rồi thu `8VB-P9Wk7v4` mức full, manifest ghi `ytdlp … disabled` cho mọi cap.)

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/settings/Sources.tsx`.
Người làm: Thi. Phụ thuộc: T32, T13, T14. Cỡ: M.

### T34: UI Settings → AI providers

Trang làm mục 6–7 của Settings: danh sách nhà cung cấp cho nhập key, nhập `base_url` với loại `openai_compat`, nút Test; bảng gán mỗi tác vụ AI với danh sách `(provider, model)` theo thứ tự ưu tiên. Giao diện chỉ cho chọn nhà cung cấp và model, không có lựa chọn theo quốc gia, và chỉ cho gán `media.vision` cho model có khả năng `vision`.

Nghiệm thu:

- [x] Đổi nhà cung cấp của `analysis.classify` trên giao diện rồi chạy phân tích lại thì nghi vấn ghi đúng nhà cung cấp mới. (classify bị bỏ ở T56; chỉ quan sát OpenRouter ở tác vụ này, định tuyến hai chiều kiểm qua `media.vision`, Gemini trả lỗi nhà cung cấp chứ không phải kết quả thành công)
- [x] Đổi nhà cung cấp của `media.vision` thì `vision.json` lần sau ghi đúng nhà cung cấp mới.

Giao diện đã nối API T32 (team làm theo đồng ý của người dùng). Từ 21/11, ô `analysis.classify` bị bỏ (T56); T34 chỉ ghi nhận `classify` qua OpenRouter, còn định tuyến hai chiều đã kiểm qua `media.vision`. Việc kiểm đổi nhà cung cấp của `analysis.video_verdict` chuyển sang T53 / Checkpoint 6c. Trước đó ô `analysis.classify` chờ T23; ô `media.vision` dựa vào T21 (`vision.json` đã ghi provider/model), có thể nghiệm thu thủ công bằng key gemini hoặc openrouter.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/settings/AIProviders.tsx`.
Người làm: Bảo. Phụ thuộc: T32, T13, T17, T21, T23. Cỡ: M.

### T35: UI Dashboard

Hoàn thiện trang dashboard đã có từ T31: số kênh, số video, số lần thu; số nghi vấn theo severity và theo trạng thái rà soát; biểu đồ hoạt động theo ngày; lượng quota và credit đã dùng. Dòng sự kiện giữ nguyên.

Nghiệm thu:

- [x] Số liệu khớp với chỉ mục. (Nghiệm thu 19/11 trên Chrome: 4 kênh, 41 video, 45 bản thu, 1 nghi vấn medium, needs_info 1, khớp thư mục `data/` và `index.db`.)
- [x] Trang tải dưới 1 giây với dữ liệu demo. (20/11: bản build production, 77 video và 231 nghi vấn, số liệu hiện xong trong 283–339 ms cả 5 lần; xem `docs/spikes/latency.md`.)

Kiểm tra: `npm run build` và kiểm tra thủ công.

Backend xong: `GET /api/dashboard` (số kênh, video, bản thu; nghi vấn theo severity và trạng thái; hoạt động 14 ngày; video nổi bật tính high 3, medium 2, low 1, bỏ nghi vấn đã bác, hoà thì nhiều view hơn). `youtube_quota` và `supadata_credits` là null tới khi có T14, T15. `GET /api/events` có thêm tiêu đề video, tên kênh, số nghi vấn, lỗi và sự kiện `review`.

File: `api/dashboard.py`, `web/src/pages/Dashboard.tsx`.
Người làm: Thi. Phụ thuộc: T31, T32, T25, T15, T13. Cỡ: M.

### Checkpoint F

Gồm các task: T15, T24, T27, T28, T29, T33, T34, T35, T40, T41, T45, T46.

- [ ] Rà lại từng tiêu chí ở SPEC §8 và đánh dấu đạt hay chưa.
- [ ] `uv run pytest`, `ruff` và `npm run build` đều sạch.

## Phase 7: Demo

### T36: Dữ liệu demo

Thu và xử lý 10–20 video thật cho demo, tạo đối tượng demo kèm ảnh mẫu. Đối tượng demo dùng khuôn mặt của một thành viên nhóm. Dữ liệu demo phải có ít nhất một video mà nghi vấn hình ảnh nằm ở đoạn không ai nhắc tên. Chuẩn bị sẵn video ngắn cho màn 2, và chọn kênh tin tức cho watchlist ở màn 3.

Nghiệm thu:

- [ ] Dữ liệu demo có ít nhất một nghi vấn speech, một ocr, một visual, và một nghi vấn visual ở đoạn không nhắc tên.
- [ ] Chạy theo checklist (T42) từ đầu đến cuối không gặp lỗi.

Kiểm tra: chạy theo checklist.

Người làm: cả hai. Phụ thuộc: Checkpoint F, T42. Cỡ: S.

### T37: Diễn tập, đo và tối ưu thời gian xử lý

Diễn tập 3 màn ít nhất 2 lần và đo thời gian, sửa các lỗi phát hiện được, rồi quay video dự phòng cho cả 3 màn. Đo màn 3 theo cả hai cách: chờ poll tự động và bấm Check now.

Nghiệm thu:

- [ ] Kết quả đo của cả 2 lần diễn tập được ghi lại và so với mục tiêu ở SPEC §8.
- [ ] Đã có video dự phòng.

Kiểm tra: ghi kết quả vào `docs/spikes/latency.md`.

Người làm: cả hai. Phụ thuộc: T36. Cỡ: S.

### T38 (làm thêm): Bảng so sánh tĩnh và LLM

Gán nhãn tay khoảng 50 đoạn, tính precision và recall của tầng tĩnh và tầng LLM để đưa vào báo cáo môn học. Từ 21/11, tầng phân loại văn bản là Jev (T55, T56), nên bảng so tầng tĩnh với Jev.

Nghiệm thu:

- [ ] `docs/eval/static-vs-llm.md` có bảng số liệu và nhận xét.

Kiểm tra: đọc và duyệt file kết quả.

Người làm: Bảo. Phụ thuộc: T24. Cỡ: S.

### T47: `analysis`: phân loại comment và lời nói bằng Jev

Từ 21/11: cấu hình câu hỏi được thay bằng R10 ở T54; mục nghiệm thu về 42 dòng chưa gán được thay bằng phép đo của T54.

Theo SPEC 10.6 (bước 3): Jev xét mọi đoạn lời nói và mọi comment của video, không chỉ chỗ nhắc tên; câu hỏi `category`, `target` (đối tượng hoặc `none`), `severity`. Module `analysis/jev.py` gọi API bằng thư viện chuẩn hoặc httpx, đọc key qua `h4wk.core.secrets`, một request mỗi đoạn hoặc comment, chạy song song có giới hạn, thử lại khi 429 theo `retry-after`. Bỏ tác vụ `analysis.classify_comment` và module `analysis/comments.py`; lời nói không gửi LLM nữa. Không có LLM dự phòng. `ModelRef.provider` là `typesafe`, `analyzer` giữ `llm`. `h4wk init` thêm sẵn đối tượng "Đảng và Nhà nước Việt Nam".

Nghiệm thu:

- [ ] Gán nhãn đủ 124 dòng ở `data/eval/jev/trial.csv` (còn 42 dòng chưa gán); Jev đạt recall không thấp hơn LLM trên cùng bộ nhãn.
- [x] Chạy thử trên mọi đoạn và comment của 8 video có sẵn, gán nhãn khoảng 50 mục không nhắc tên ai mà Jev đánh dấu, ghi precision vào `docs/eval/`.
- [x] Test với Jev giả: đoạn và comment vi phạm sinh nghi vấn đúng danh mục và đối tượng; `target` là `none` thì không sinh nghi vấn; 429 được thử lại; Jev lỗi thì job vẫn xong, lỗi ghi vào `llm_error`.
- [x] Thiếu `TYPESAFE_API_KEY` thì Settings báo thiếu key; job vẫn chạy, comment và lời nói chỉ có tầng tĩnh.

Kiểm tra: `uv run --no-sync pytest tests/unit/test_jev.py`, chạy thật trên 8 video có sẵn.

Người làm: Thi. Phụ thuộc: T24. Cỡ: M.

### T48: `analysis`: kết luận theo video

Bước 4 ở SPEC 10.6: tác vụ AI `analysis.video_verdict`, cấu trúc `VideoVerdict` trong C4, file `verdict.json`. Thêm ví dụ hợp lệ và bị từ chối vào `test_contracts.py`, chạy lại `h4wk schema export`.

Nghiệm thu:

- [x] Video không có nghi vấn vi phạm có kết luận `no` mà không gọi LLM.
- [x] `finding_id` trong kết luận đều là nghi vấn của cùng lần chạy; đầu ra LLM sai schema không được ghi.
- [x] Trên video `1RUJ_6eruwA`, kết luận `yes`, danh mục thuộc nhóm vi phạm và khớp với danh mục nghi vấn, tóm tắt nhắc tới dòng chữ “chính quyền Tô Lâm mới là kẻ khủng bố” hoặc cáo buộc bắt cóc. Run `r_01M7XX549VDRXKCYH11Y3K4VYM` trên bản sao trả `yes` và `unsupported_accusation`.

Người làm: Thi. Phụ thuộc: T23. Cỡ: M.

### T49: `review`: rà soát theo video (backend)

SPEC 10.8: hàng đợi theo video (kết luận `yes` hoặc `uncertain` của lần chạy mới nhất), quyết định gắn với `video_id` và `run_id` trong `reviews.jsonl`, API liệt kê và ghi quyết định. Dựng lại chỉ mục (T45) đọc được quyết định mới.

Nghiệm thu:

- [x] Video kết luận `no` không có trong hàng đợi.
- [x] Thu lại video thì kết luận mới bắt đầu ở trạng thái chưa rà soát, quyết định cũ vẫn còn.

Người làm: Thi. Phụ thuộc: T48. Cỡ: M.

### T50: UI rà soát theo video

Review queue liệt kê video; mở một video thấy thẻ kết luận (danh mục, mức độ, tóm tắt) phía trên trình phát, bằng chứng nhóm theo loại (chữ trên hình, lời nói, comment, hình ảnh), bấm bằng chứng thì tua tới đúng chỗ. Nút xác nhận, bác bỏ, cần thêm thông tin cho cả video, có phím tắt như màn hiện tại.

Nghiệm thu:

- [x] Video `1RUJ_6eruwA` duyệt xong bằng một lần bấm.
- [x] `npm run build` và `npm run lint` không lỗi.

Người làm: Thi. Phụ thuộc: T49. Cỡ: M.

## Phase 6c: AI cục bộ và Jev cho mọi văn bản (thêm ngày 2026-11-21)

Spec: [SPEC-local-ai.md](../SPEC-local-ai.md). Ollama chạy ở máy GPU riêng trong LAN; IP chỉ ghi trong `config/ai.toml` (không commit). Kết quả đo dùng làm căn cứ: `data/eval/jev/tune/REPORT.md` (Jev R10) và `data/eval/ollama/REPORT.md` (chọn `qwen3-vl:4b`).

Thứ tự: T51 → (T52, T54, T56 song song) → T53 sau T52 → T55 sau T54 → T57.

### T51: `ai-gateway`: nhà cung cấp `ollama`

C5 thêm `type = "ollama"`: bắt buộc `base_url`, không cần key, dùng adapter `openai_compat`. Settings thêm được nhà cung cấp Ollama, thẻ Ollama không có ô API key, route tới Ollama không báo thiếu key.

Nghiệm thu:

- [x] Test hợp đồng: ví dụ hợp lệ, ví dụ thiếu `base_url` bị chặn đúng quy tắc; `make_provider` tạo được provider Ollama khi không có key.
- [x] Backend pytest, ruff; web build, lint qua.

Đã làm ở nhánh `feat/ollama-provider` (commit `9c8037d`).

Người làm: Thi. Phụ thuộc: T17, T34. Cỡ: M.

### T52: `media`: mô tả ảnh qua Ollama, cache theo từng ảnh

Merge nhánh `feat/t21-vision-live` trước (đã có làm mới cache theo prompt). Prompt `media.vision` thêm câu “Trả lời ngắn gọn, không cần suy luận dài.”. Request tới nhà cung cấp loại `ollama` có thời gian chờ 300 giây và `max_tokens` 1024; nhà cung cấp khác giữ nguyên 120 giây. `vision.json` được ghi lại sau mỗi ảnh mô tả xong (ghi nguyên tử, hai luồng không ghi đè lẫn nhau). Khoá cache một ảnh gồm hash ảnh, prompt, `provider` và `model`; bỏ hash của toàn bộ `ai.toml`.

Nghiệm thu:

- [ ] Test: ảnh đã có trong cache với cùng prompt và route thì không gọi gateway; sửa tuyến `analysis.video_verdict` không làm mô tả lại ảnh; đổi prompt thì mô tả lại.
- [ ] Test: dừng (ném lỗi) sau ảnh thứ 2 của 4 ảnh, chạy lại thì chỉ gọi gateway cho 2 ảnh còn lại.
- [ ] Test: provider Ollama gửi `timeout=300` và `max_tokens=1024`; provider `openai_compat` khác không đổi.
- [ ] Chạy thật trên một video ngắn có sẵn với `config/ai.toml` trỏ Ollama: `vision.json` ghi `provider: ollama`, `model: qwen3-vl:4b`; ghi thời gian mỗi ảnh vào `docs/eval/local-ai.md`.

Kiểm tra: `cd backend && uv run --no-sync pytest tests/unit/test_vision.py tests/unit/test_ai_providers.py`.

File: `media/vision.py`, `media/prompts/vision.md`, `ai/providers/__init__.py` hoặc `ai/providers/openai_compat.py`, `ai/base.py`, tests.
Người làm: Thi. Phụ thuộc: T51, T21. Cỡ: M.

### T53: `analysis`: kết luận theo video bằng model cục bộ

Đổi tuyến mặc định của `analysis.video_verdict` (và `media.vision`) trong `config/ai.toml.example` thành `ollama/qwen3-vl:4b` trước, sau đó Gemini, OpenRouter, Anthropic. Viết script đánh giá chạy `verdict.decide` qua gateway thật trên các bản thu đã có nghi vấn vi phạm, ghi kết quả ra `data/eval/verdict-local/`.

Nghiệm thu:

- [ ] Trên ít nhất 5 video có nghi vấn vi phạm: JSON hợp lệ (ngay lần đầu hoặc sau lượt sửa của gateway), tóm tắt tiếng Việt có dấu, `finding_ids` thuộc cùng lần chạy; Thi chấm đạt ít nhất 4/5.
- [ ] Tắt Ollama thì kết luận chuyển sang tuyến cloud kế tiếp có key, `model` trong `verdict.json` ghi đúng tuyến đó.
- [ ] Ghi số liệu (thời gian, số lượt sửa JSON, điểm chấm) vào `docs/eval/local-ai.md`.
- [ ] Đổi route `analysis.video_verdict` trên Settings có hiệu lực (`ai_calls.jsonl` ghi đúng provider).

Kiểm tra: chạy script đánh giá; `uv run --no-sync pytest tests/unit/test_verdict.py`.

File: `config/ai.toml.example`, `docs/eval/local-ai.md`, script trong `data/eval/verdict-local/` (không commit).
Người làm: Thi. Phụ thuộc: T52. Cỡ: S.

### T54: `analysis`: Jev cấu hình R10 cho lời nói và comment

Áp `data/eval/jev/tune/final_questions.json` vào `analysis/jev.py`: `state` có `protected_targets`, `source_type`, `text` và ngữ cảnh theo loại; câu hỏi `category` (criteria `{what, examples}`), `severity`, `is_attack`, `target`; bỏ `about_protected`. Giữ nghi vấn khi `is_attack.noul ≥ 0,5` và `target.choice ≠ "none"`. `protected_targets` và `target.criteria` sinh từ danh sách đối tượng (tên, biệt danh, viết tắt), không viết cứng. Cập nhật SPEC-local-ai.md nếu cách mô tả đối tượng khác R10.

Nghiệm thu:

- [ ] Test với Jev giả: `is_attack` 0,49 thì không giữ, 0,5 thì giữ; `target` là `none` thì không giữ; hai đối tượng sinh hai khoá trong `target.criteria`.
- [ ] Chạy `analysis/jev.py` mới trên bộ test 119 mục của `data/eval/jev/tune/` (gọi API thật): P và R trong khoảng ±0,02 so với R10 (P 0,754 / R 0,920). Lệch hơn thì ghi nguyên nhân và hỏi Thi trước khi chỉnh.
- [ ] Đóng T47: thay mục “gán nốt 42 dòng” bằng kết quả này.

Kiểm tra: `uv run --no-sync pytest tests/unit/test_jev.py`.

File: `analysis/jev.py`, `tests/unit/test_jev.py`, script đối chiếu trong `data/eval/jev/tune/`.
Người làm: Thi. Phụ thuộc: T47. Cỡ: M.

### T55: `analysis`: Jev cho tiêu đề, mô tả, OCR, hình ảnh và thumbnail

Thêm vào Jev các mục: tiêu đề video (`source_kind: title`), mô tả video (`description`), mỗi đoạn timeline có OCR hoặc mô tả ảnh (`text` là các dòng OCR không trùng ghép bằng ` | ` cùng mô tả ảnh và `offensive_cues`; `source_kind` là `ocr` khi có chữ, `visual` khi chỉ có hình; kèm `frame`), mỗi thumbnail có OCR hoặc mô tả ảnh (`thumbnail`). Xét mọi mục loại này, không chỉ mục có dấu hiệu tên. `quote` là văn bản đã gửi; `reason` ghi danh mục và xác suất như hiện nay.

Nghiệm thu:

- [ ] Test với Jev giả: mỗi loại nguồn sinh nghi vấn đúng `source_kind`, `segment_id`, `start`, `frame`; dòng OCR lặp giữa các keyframe chỉ gửi một lần.
- [ ] Chạy thật trên `1RUJ_6eruwA`: dòng chữ “CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ” sinh nghi vấn `ocr` hoặc `visual` từ Jev.
- [ ] Ghi số request Jev thêm cho mỗi video vào `docs/eval/local-ai.md`.

Kiểm tra: `uv run --no-sync pytest tests/unit/test_jev.py tests/integration/test_pipeline.py`.

File: `analysis/jev.py`, `analysis/runner.py`, tests.
Người làm: Thi. Phụ thuộc: T54. Cỡ: M.

### T56: Bỏ tác vụ AI `analysis.classify`

Xoá `analysis/llm.py` và lời gọi trong `analysis/runner.py`. C5 bỏ `AiTask.CLASSIFY`; cấu hình cũ còn tuyến `analysis.classify` vẫn đọc được, tuyến bị bỏ qua và ghi cảnh báo (như `analysis.classify_comment`). Trang Settings bỏ dòng `analysis.classify`. Cập nhật `ai.toml.example`, chạy lại `h4wk schema export` và sinh lại kiểu API. `analysis/evaluation.py` (T38) chuyển sang so tầng tĩnh với Jev.

Nghiệm thu:

- [ ] Test hợp đồng: cấu hình có `analysis.classify` nạp được, có cảnh báo, `tasks` không còn khoá này; ví dụ hợp lệ và bị từ chối được cập nhật.
- [ ] `grep -rn "analysis.classify"` trong `backend/src`, `web/src`, `config/ai.toml.example` không còn kết quả (trừ chỗ đọc cấu hình cũ).
- [ ] Backend pytest, ruff; web build, lint qua.

Kiểm tra: lệnh test, lint và build chung.

File: `analysis/llm.py` (xoá), `analysis/runner.py`, `core/config_models.py`, `web/src/api/settings.ts`, `web/src/components/settings/ai/TaskRoutes.tsx`, tests, `docs/contracts/c5-ai.json`.
Người làm: Thi. Phụ thuộc: T55 (để không mất phân loại OCR/hình ở giữa hai task; làm song song được nếu merge sau T55). Cỡ: M.

### T57: UI ẩn lý do của nghi vấn Jev

Danh sách nghi vấn và màn rà soát không hiện `reason` của nghi vấn có `model.provider` là `typesafe`. Nghi vấn tầng tĩnh vẫn hiện nhóm và cụm từ khớp. `reason` vẫn nằm trong `findings.json`.

Nghiệm thu:

- [x] Mở `1RUJ_6eruwA`: không còn chuỗi `Jev:` trên giao diện; nghi vấn tĩnh vẫn có dòng Reason.
- [x] `npm run build` và `npm run lint` không lỗi.

Kiểm tra: build và kiểm tra thủ công.

File: `web/src/pages/FindingsPage.tsx`, `web/src/pages/FindingReviewPage.tsx`.
Người làm: Thi. Phụ thuộc: không. Cỡ: S.

### Checkpoint 6c

- [ ] Xử lý một video thật ở mức `full` với cấu hình mẫu mới: `ai_calls.jsonl` không có lời gọi cloud cho `media.vision` và `analysis.video_verdict` khi Ollama chạy.
- [ ] Đủ 8 tiêu chí thành công của SPEC-local-ai.md.
- [ ] Gộp SPEC-local-ai.md vào SPEC.md (§10.4, §10.5, §10.6, §13), đổi `Status` thành `implemented`.
