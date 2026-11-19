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
- [ ] Nếu không cài chung được, file ghi phương án dự phòng đã thử được (PaddleOCR chạy CPU, hoặc tách môi trường cho worker `gpu`).

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

- [ ] Từ trình duyệt làm trọn được luồng: đăng nhập, thêm đối tượng, dán link, chờ job chạy xong, thấy nghi vấn.
- [ ] Job lỗi hiện thông báo lỗi trên trang Collect.

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

- [ ] Phần chuyển sang dữ liệu chung có test dùng response đã ghi sẵn.
- [ ] Tắt yt-dlp thì metadata, comment và thumbnail vẫn thu được; manifest ghi yt-dlp là `disabled` và `MEDIA` là `no_source`; job vẫn chạy phân tích phần văn bản.

Kiểm tra: `uv run pytest tests/unit/test_ytapi_normalize.py` và `uv run pytest -m live -k ytapi`.

File: `collectors/providers/youtube_api.py`, `collectors/quota.py`, fixtures, tests.
Người làm: Thi. Phụ thuộc: T8. Cỡ: M.

### T15: Adapter Supadata và credit

`SupadataCollector` hỗ trợ `TRANSCRIPTS` và `VIDEO_METADATA`. Transcript do AI của Supadata tạo được gắn nhãn `supadata_ai`. Với transcript lấy từ phụ đề YouTube, nhãn lấy theo thông tin Supadata trả về; nếu API không cho biết là `uploaded` hay `auto` thì gắn `supadata_ai` và ghi chú lại. Credit được đếm theo tháng.

Nghiệm thu:

- [ ] Phần chuyển sang dữ liệu chung có test dùng response đã ghi sẵn.
- [ ] Khi bật `fault_injection` cho yt-dlp, Supadata được gọi thay để lấy transcript, và manifest ghi đủ cả hai lần gọi.

Kiểm tra: `uv run pytest tests/unit/test_supadata.py tests/unit/test_orchestrator.py`.

File: `collectors/providers/supadata.py`, fixtures, tests.
Người làm: Thi. Phụ thuộc: T8. Cỡ: S.

### T45: `core`: dựng lại database chỉ mục

`h4wk reindex` xoá chỉ mục cũ rồi dựng lại từ `data/`: đối tượng, video, bản thu, nghi vấn của lần chạy mới nhất, và quyết định rà soát trong `reviews.jsonl`. Tài khoản, watchlist và lịch sử job không được dựng lại; đây là hạn chế đã chấp nhận ở SPEC 10.1.

Nghiệm thu:

- [ ] Xoá `index.db` rồi chạy `reindex` thì API trả về đối tượng, video và nghi vấn như trước.
- [ ] Quyết định rà soát trong một `reviews.jsonl` mẫu được nạp lại đúng.

Kiểm tra: `uv run pytest tests/integration/test_reindex.py`.

File: `src/h4wk/core/reindex.py`, `cli.py`, `tests/integration/test_reindex.py`.
Người làm: Thi. Phụ thuộc: T6, T44. Cỡ: S.

### T46: `jobs`: chạy lại job bị treo và xử lý playlist

Khi worker khởi động, job đang ở trạng thái `running` được đưa lại vào hàng đợi; nhờ các bước idempotent, job chạy tiếp từ bước dở dang. Link playlist được tách thành các job, mỗi video một job, tối đa 50 video (cấu hình được).

Nghiệm thu:

- [ ] Integration test tắt worker giữa chừng rồi bật lại; job chạy tiếp tới `done` và không làm lại bước đã xong.
- [ ] Dán link một playlist có 3 video (dùng adapter giả) thì tạo đúng 3 job.

Kiểm tra: `uv run pytest tests/integration/test_recovery.py tests/unit/test_playlist.py`.

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

- [ ] Mỗi nhà cung cấp đã có key chạy được một lời gọi văn bản trong `-m live`, trả về đối tượng hợp lệ.
- [ ] Mỗi nhà cung cấp có model đọc ảnh chạy được một lời gọi ảnh.

Đã triển khai ba adapter và kiểm thử qua SDK. Nghiệm thu live đang chờ API key.

Kiểm tra: `uv run pytest -m live -k ai_provider`.

File: `src/h4wk/ai/providers/{anthropic.py,openai_compat.py,gemini.py}`, `config/ai.toml.example`, tests.
Người làm: Bảo. Phụ thuộc: T16. Cỡ: M.

### Checkpoint B

- [ ] Có test chứng minh việc chuyển nguồn thu khi lỗi.
- [ ] Đổi nhà cung cấp của một tác vụ AI trong `ai.toml` mà không sửa code, và lời gọi live vẫn chạy.

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

Kiểm tra tích hợp với nhà cung cấp giả bằng `uv run pytest tests/integration/test_pipeline.py -k full_flow`. Nghiệm thu VLM thật cần API key.

File: `src/h4wk/media/vision.py`, `media/prompts/vision.md`, tests.
Người làm: Bảo. Phụ thuộc: T17, T19. Cỡ: S.

### T22: Timeline đầy đủ

Kết quả OCR và VLM được gắn vào đoạn theo thời gian `t` của khung; kết quả trên thumbnail được ghi vào khối `thumbnails`. Timeline ghi thêm `source_video_sha256` lấy từ manifest. Các bước T18–T21 được nối vào luồng `jobs` theo đúng mức thu, mỗi bước có tiến độ riêng. Task này sửa `jobs/pipeline.py` của Thi, nên hai người cần phối hợp.

Nghiệm thu:

- [x] Timeline T44 tổng hợp có đủ speech, ocr, visual và khối thumbnails, và validate được theo C3 trong kiểm thử API. STT, nhận dạng OCR và nhà cung cấp VLM được mô phỏng trong kiểm thử này.
- [ ] Màn Collect hiện đủ các bước collect → transcribe → frames → OCR/VLM → analyze.

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

- [ ] Đầu ra sai schema không bao giờ được ghi vào `findings.json`.
- [ ] Trên bản thu mẫu, LLM thật sinh được ít nhất một nghi vấn từ speech, một từ ocr và một từ visual.
- [ ] Đoạn chỉ có ảnh chế, không ai nhắc tên, vẫn được gửi đi nhờ ngữ cảnh cấp video và sinh nghi vấn `visual`.

Kiểm tra: `uv run pytest tests/unit/test_analysis_llm.py` (dùng `FakeProvider`) và `uv run pytest -m live -k analysis`.

File: `src/h4wk/analysis/{llm.py,prompts/classify.md,runner.py}`, tests.
Người làm: Bảo. Phụ thuộc: T11, T16, T22. Cỡ: M.

### T24: `analysis`: comment

Comment và reply có dấu hiệu tên (từ T11) được gửi tới tác vụ AI `analysis.classify_comment` theo lô 20–50 comment, sinh nghi vấn có `source_kind: "comment"` và `comment_id`. Số comment tối đa phân tích cho mỗi video có thể giới hạn bằng `analysis.toml`.

Nghiệm thu:

- [ ] Một video có 500 comment chạy xong với số lời gọi LLM không quá ⌈số comment có dấu hiệu / kích thước lô⌉.
- [ ] `comment_id` của nghi vấn trỏ đúng tới comment.

Kiểm tra: `uv run pytest tests/unit/test_analysis_comments.py`.

File: `analysis/{comments.py,prompts/classify_comment.md}`, tests.
Người làm: Bảo. Phụ thuộc: T23. Cỡ: S.

### T25: `review`: backend hàng đợi và quyết định

API hàng đợi chỉ trả nghi vấn của lần chạy mới nhất cho mỗi bản thu, lọc được theo video, `source_kind` và trạng thái, sắp theo severity rồi đến thời gian. `POST /api/findings/{id}/decision` nhận status `confirmed`, `rejected` hoặc `needs_info`; `rejected` bắt buộc có note. Mỗi quyết định được ghi thêm vào `reviews.jsonl` theo `finding_id` và `run_id`, ghi audit, rồi cập nhật chỉ mục. Ngoài endpoint này, code không đặt trạng thái `confirmed` ở đâu khác. Task làm và test bằng nghi vấn mẫu của T44.

Nghiệm thu:

- [x] Bác nghi vấn mà không có lý do thì nhận 422.
- [ ] Sau `reindex`, trạng thái rà soát vẫn giữ nguyên.
- [x] Chạy phân tích lại thì nghi vấn của lần chạy mới ở trạng thái chưa rà soát; quyết định của lần chạy trước vẫn còn trong `reviews.jsonl`.

Kiểm tra: `uv run pytest tests/unit/test_review.py`.

API: `GET /api/review/queue?video=&source_kind=&status=` trả `{finding, status, video: {id, title, channel}, decisions[]}`; `POST /api/findings/{id}/decision`; `GET /api/findings/{id}/decisions` (mới nhất trước). Mục giữ trạng thái sau `reindex` chờ T45. Tham số `latest_only=true` (queue, findings, videos, dashboard) chỉ giữ bản thu mới nhất mỗi video.

File: `src/h4wk/review/{queue.py,decisions.py}`, `api/review.py`, tests.
Người làm: Thi. Phụ thuộc: T12, T44, T45. Tích hợp sau: T11, T23. Cỡ: S.

### T26: UI Video detail: trình phát, transcript, thanh thời gian

Backend có endpoint stream bản proxy, hỗ trợ Range. Trang Video detail có trình phát `<video>`, transcript tự cuộn theo thời gian phát kèm dropdown chọn loại transcript để xem, và thanh thời gian tô màu các đoạn có nghi vấn theo severity. Mở trang với `?t=` hoặc `?finding=` thì video phát từ `start − 2s`.

Nghiệm thu:

- [ ] Bấm một nghi vấn trong bảng thì video nhảy đúng tới vị trí đó và đoạn tương ứng được tô sáng.

Kiểm tra: `npm run build`, rồi kiểm tra thủ công trên 2 video.

Backend đọc video đã có ở `api/videos.py` (Thi làm trước để giao diện nối): `GET /api/videos`, `/api/videos/{id}`, `/timeline`, `/transcripts`, `/comments`, `/media` (proxy hoặc file gốc, hỗ trợ Range), `/frames/{file}`.

File: `api/media.py`, `web/src/pages/VideoDetail.tsx`, `web/src/components/{Player,TranscriptPane,FindingTimeline}.tsx`.
Người làm: Bảo. Phụ thuộc: T13, T22, T25. Cỡ: M.

### T27: UI Video detail: dải khung hình, comment, lịch sử bản thu

Trang có dải keyframe; bấm vào một khung thì video seek tới thời điểm đó, ảnh lớn hiện ra với khung bao của chữ OCR, khuôn mặt và ảnh mẫu đã khớp, cùng mô tả VLM bên cạnh. Tab Comments đánh dấu các comment bị gắn cờ. Tab Captures liệt kê các lần thu, dùng API của T29.

Nghiệm thu:

- [ ] Nghi vấn từ OCR hiện đúng khung hình kèm khung bao.
- [ ] Nghi vấn từ comment mở đúng comment.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/components/{FrameStrip,FrameViewer,CommentsTab,CapturesTab}.tsx`, `api/media.py`.
Người làm: Bảo. Phụ thuộc: T26, T29, T24. Tích hợp sau: T40, T41. Cỡ: M.

### T28: UI Review queue

Trang hiển thị danh sách nghi vấn với các bộ lọc. Panel bên cạnh hiện trích dẫn, khung hình, lý do, `triggers`, analyzer, model và liên kết mở trang Video detail tại đúng đoạn. Các nút Confirm, Reject (bắt buộc nhập lý do) và Needs info có phím tắt.

Nghiệm thu:

- [ ] Duyệt 10 nghi vấn liên tiếp mà không phải rời trang.
- [ ] Mỗi quyết định có một dòng tương ứng trong audit.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/ReviewQueue.tsx`, `web/src/components/FindingPanel.tsx`.
Người làm: Thi. Phụ thuộc: T25, T13. Tích hợp sau: T26. Cỡ: M.

### T29: UI Evidence và Verify integrity

Backend có API liệt kê các bản thu của một video. Trang Capture hiển thị manifest, danh sách file kèm SHA-256 và dung lượng, các nguồn đã gọi cùng trạng thái, và nút tải file gốc. Nút Verify integrity gọi `verify` rồi hiện OK, FAIL, missing hoặc unexpected cho từng file.

Nghiệm thu:

- [ ] Sửa 1 byte trên đĩa thì giao diện báo FAIL đúng file đó.

Kiểm tra: `npm run build`; thủ công: sửa 1 byte rồi bấm Verify integrity.

Backend xong: `GET /api/videos/{id}/captures/{capture}` (manifest và file), `POST …/verify` (OK, FAIL, missing, unexpected kèm SHA-256 mong đợi và thực tế, có audit), `GET …/files/{path}` (chỉ file có trong manifest). Có test sửa 1 byte. Phần giao diện do phiên UI làm.

File: `api/captures.py`, `web/src/pages/Capture.tsx`.
Người làm: Thi. Phụ thuộc: T5, T13. Cỡ: S.

### T39: Đối tượng và ảnh mẫu

Backend cho tải lên, xem và xoá ảnh mẫu của từng đối tượng, gồm hai loại: ảnh khuôn mặt và ảnh hay bị dùng lại (chân dung quen thuộc, logo). Ảnh lưu ở `data/entities/<entity_id>/refs/{face,image}/`. Trang Entities cho sửa tên, biệt danh, viết tắt và quản lý ảnh mẫu.

Nghiệm thu:

- [x] Tải ảnh lên thì file nằm đúng thư mục và có dòng audit.
- [ ] Trang Entities hiện ảnh mẫu theo hai nhóm.

Kiểm tra: `uv run pytest tests/unit/test_entities.py`, `npm run build` và kiểm tra thủ công.

Backend xong: `PATCH /api/entities/{id}`, `GET /api/entities/{id}/refs`, `POST /api/entities/{id}/refs/{face|image}` (thân request là bytes ảnh JPEG/PNG/WebP, tối đa 10 MB, tên file theo SHA-256), `GET`/`DELETE` từng ảnh; `GET /api/entities` có `ref_counts`. Phần giao diện do phiên UI làm.

File: `src/h4wk/core/entities.py`, `api/entities.py`, `web/src/pages/Entities.tsx`, tests.
Người làm: Thi. Phụ thuộc: T6, T13. Cỡ: M.

### T40: `analysis`: khớp ảnh mẫu

Model embedding chọn ở T3 tính embedding cho ảnh mẫu loại `image`, cho từng keyframe, thumbnail và các ô cắt theo lưới (ví dụ 2×2 và 3×3). Ô hoặc khung có độ tương đồng vượt ngưỡng (cấu hình được) sinh dấu hiệu `via: ref_image` có frame, bbox của ô và điểm số. Dấu hiệu này được tầng LLM của T23 dùng như các dấu hiệu khác.

Nghiệm thu:

- [ ] Ảnh mẫu bị cắt một nửa, đổi màu hoặc ghép vào góc khung vẫn khớp trong clip thử.
- [ ] Clip không chứa ảnh mẫu không sinh dấu hiệu nào.

Kiểm tra: `uv run pytest tests/unit/test_refimages.py`.

File: `src/h4wk/analysis/refimages.py`, `tests/fixtures/refs/*`, tests.
Người làm: Bảo. Phụ thuộc: T39, T19, T23. Cỡ: M.

### T41: `analysis`: khớp khuôn mặt

Model khuôn mặt chọn ở T3, chạy trên máy qua hàng đợi `gpu`, phát hiện khuôn mặt trong keyframe và thumbnail rồi so với ảnh khuôn mặt mẫu của các đối tượng. Khuôn mặt khớp sinh dấu hiệu `via: face` có frame, bbox và điểm số. Đặc trưng của khuôn mặt không khớp chỉ nằm trong bộ nhớ và không được ghi ra đĩa. Tính năng có thể tắt bằng `analysis.toml`.

Nghiệm thu:

- [ ] Trên bản thu mẫu, đoạn ảnh chế khuôn mặt thành viên nhóm sinh dấu hiệu `face`.
- [ ] Khuôn mặt của người khác trong clip thử không sinh dấu hiệu, và không có file nào chứa đặc trưng của họ.
- [ ] Tắt tính năng trong `analysis.toml` thì bước này bị bỏ qua.

Kiểm tra: `uv run pytest tests/unit/test_faces.py` (đánh dấu `gpu` nếu cần).

File: `src/h4wk/analysis/faces.py`, `tests/fixtures/faces/*`, tests.
Người làm: Bảo. Phụ thuộc: T39, T19, T3, T23, T44 (video thật; bộ dò khuôn mặt không nhận ra hình vẽ của bản tổng hợp). Cỡ: M.

### T42: Checklist demo

Viết `docs/demo-checklist.md` gồm bước chuẩn bị máy (khởi động API, hai worker, frontend), các bước của 3 màn demo và kết quả mong đợi ở mỗi bước. Checklist được chạy cuối mỗi tuần từ tuần 3 và cập nhật khi có tính năng mới.

Nghiệm thu:

- [ ] Một người không viết checklist làm theo được từ đầu đến cuối.

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

- [ ] Làm trọn màn 3 chỉ bằng giao diện, và thấy sự kiện trên dashboard.

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

- [ ] Tắt yt-dlp trên giao diện rồi thu một video thì manifest ghi yt-dlp là `disabled`.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/settings/Sources.tsx`.
Người làm: Thi. Phụ thuộc: T32, T13, T14. Cỡ: M.

### T34: UI Settings → AI providers

Trang làm mục 6–7 của Settings: danh sách nhà cung cấp cho nhập key, nhập `base_url` với loại `openai_compat`, nút Test; bảng gán mỗi tác vụ AI với danh sách `(provider, model)` theo thứ tự ưu tiên. Giao diện chỉ cho chọn nhà cung cấp và model, không có lựa chọn theo quốc gia, và chỉ cho gán `media.vision` cho model có khả năng `vision`.

Nghiệm thu:

- [ ] Đổi nhà cung cấp của `analysis.classify` trên giao diện rồi chạy phân tích lại thì nghi vấn ghi đúng nhà cung cấp mới.
- [ ] Đổi nhà cung cấp của `media.vision` thì `vision.json` lần sau ghi đúng nhà cung cấp mới.

Kiểm tra: `npm run build` và kiểm tra thủ công.

File: `web/src/pages/settings/AIProviders.tsx`.
Người làm: Bảo. Phụ thuộc: T32, T13, T17, T23. Cỡ: M.

### T35: UI Dashboard

Hoàn thiện trang dashboard đã có từ T31: số kênh, số video, số lần thu; số nghi vấn theo severity và theo trạng thái rà soát; biểu đồ hoạt động theo ngày; lượng quota và credit đã dùng. Dòng sự kiện giữ nguyên.

Nghiệm thu:

- [ ] Số liệu khớp với chỉ mục.
- [ ] Trang tải dưới 1 giây với dữ liệu demo.

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

Gán nhãn tay khoảng 50 đoạn, tính precision và recall của tầng tĩnh và tầng LLM để đưa vào báo cáo môn học.

Nghiệm thu:

- [ ] `docs/eval/static-vs-llm.md` có bảng số liệu và nhận xét.

Kiểm tra: đọc và duyệt file kết quả.

Người làm: Bảo. Phụ thuộc: T24. Cỡ: S.

### T43: Báo cáo môn học

Viết báo cáo môn học: mục tiêu, kiến trúc, phương pháp lưu bằng chứng, cách phân tích, kết quả đo, giới hạn. Báo cáo giải thích lý do dùng khớp khuôn mặt (đảo ngược quy định trong mô tả gốc), các giới hạn đã áp dụng, và cơ sở theo Nghị định 13/2023.

Nghiệm thu:

- [ ] Hai người đã đọc và duyệt bản cuối.

Kiểm tra: đọc và duyệt.

Người làm: cả hai. Phụ thuộc: T37. Cỡ: S.
