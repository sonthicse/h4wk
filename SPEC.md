# Spec: h4wk, công cụ SOCMINT cho YouTube (V1, bản demo)

> Trạng thái: đã duyệt có sửa đổi, cập nhật lần cuối ngày 2026-11-18 sau vòng review.
> Spec dựa trên [statement of intent](docs/intent/socmint-youtube.md) đã xác nhận và [mô tả gốc](.tmp/MO_TA_DU_AN.md). Khi ba tài liệu mâu thuẫn, SPEC.md được ưu tiên, sau đó đến intent, cuối cùng là mô tả gốc.
> Toàn bộ spec nằm trong file này. Phần dùng chung viết một lần; mỗi module có một mục ngắn ở [phần 10](#10-đặc-tả-từng-module).

## 1. Mục tiêu

Công cụ web giúp analyst phát hiện nội dung bôi nhọ một đối tượng cụ thể trên YouTube (kịch bản K1). Nội dung được phân tích từ lời nói, chữ trên hình, hình ảnh, tiêu đề, mô tả, thumbnail và comment. Hình ảnh còn được so với ảnh mẫu và khuôn mặt mẫu của đối tượng. Dữ liệu thu về được lưu làm bằng chứng và truy vết được nguồn gốc. Mọi kết quả phân tích chỉ là nghi vấn cho đến khi analyst rà soát.

Người dùng là hai thành viên nhóm trong vai analyst. Thi là người chịu trách nhiệm chính. Người cần thuyết phục là người chấm trong buổi demo, vào khoảng cuối tháng 12/2026. Nhóm xác nhận thời gian không phải ràng buộc, và việc viết code có coding agent hỗ trợ. Ba màn demo được mô tả ở [phần 8](#8-tiêu-chí-thành-công).

Dự án đang ở giai đoạn thử nghiệm. Một số hạn chế được nhóm chấp nhận có ghi ở mục của từng module.

## 2. Bản đồ module (đã duyệt)

| Module id | Trách nhiệm | Phụ thuộc | Hợp đồng cung cấp |
|---|---|---|---|
| `case-core` | Case, đối tượng và ảnh mẫu của đối tượng, 2 tài khoản, nhật ký, database chỉ mục, cấu hình và lưu secret | không có | Mô hình Case/Đối tượng, `audit.log()`, C5: định dạng file cấu hình |
| `evidence-store` | Bản thu được khoá chống sửa nhầm, manifest, SHA-256, tách dữ liệu gốc và phái sinh, kiểm tra toàn vẹn | `case-core` | C1: cấu trúc bản thu |
| `collectors` | Hợp đồng adapter, danh sách nguồn thu, điều phối theo thứ tự ưu tiên và chuyển nguồn khi lỗi; adapter yt-dlp, YouTube API, Supadata | `evidence-store` | C2: mô hình dữ liệu chung, giao diện `Collector` |
| `ai-gateway` | Nhiều nhà cung cấp LLM/VLM, định tuyến theo tác vụ AI, kiểm tra đầu ra có cấu trúc, chuyển nhà cung cấp khi lỗi, ghi chi phí | `case-core` | Giao diện `AIGateway` |
| `media-pipeline` | Bản 480p, tách audio, speech-to-text, keyframe theo mức thay đổi, OCR, VLM, ghép timeline | `evidence-store`, `ai-gateway` | C3: cấu trúc timeline |
| `analysis` | Tìm dấu hiệu đối tượng (tên, khuôn mặt, ảnh mẫu), lọc tĩnh rồi LLM trên timeline, tiêu đề, mô tả, thumbnail và comment | `media-pipeline`, `ai-gateway`, `case-core` | C4: dấu hiệu, nghi vấn và quyết định rà soát |
| `jobs` | Chạy tác vụ nền, nối luồng thu → xử lý → phân tích, tiến độ, thử lại khi lỗi | `collectors`, `media-pipeline`, `analysis` | API gửi job và xem tiến độ |
| `review` | Hàng đợi rà soát, quyết định kèm nhật ký | `analysis`, `evidence-store` | không có |
| `watchlist` | Kiểm tra RSS của kênh, phát hiện video mới, nút Check now, dòng sự kiện | `collectors`, `jobs` | không có |
| `web-ui` | Khung ứng dụng React, giao diện tiếng Anh. Màn hình của module nào nằm trong mục của module đó | API của các module | không có |

`analysis` là module phân tích chung. V1 chỉ cài bộ phân tích cho K1; các kịch bản khác sau này thêm vào cùng module.

Việc đầu tiên là dựng một luồng tối giản chạy được từ đầu đến cuối, sau đó mới làm sâu từng phần (chi tiết ở [phần 9](#9-thứ-tự-làm-và-mốc-kiểm-tra)). Năm hợp đồng C1–C5 được chốt vào cuối tuần 1. Sau mốc này, mọi thay đổi hợp đồng phải được Thi đồng ý.

Một số từ dùng thống nhất trong các tài liệu:

| Từ | Nghĩa |
|---|---|
| nguồn thu | Một adapter thu thập: yt-dlp, YouTube API, Supadata |
| nhà cung cấp AI | Một dịch vụ LLM/VLM: Anthropic, OpenAI, DeepSeek… |
| tác vụ AI | Khoá định tuyến trong `ai.toml`, ví dụ `analysis.classify` |
| bước | Một bước trong luồng xử lý của một job, ví dụ transcribe, OCR |
| task | Một hạng mục công việc T1–T46 trong `tasks/todo.md` |
| bản thu | Kết quả một lần thu, nằm trong `captures/<ts>/` |
| dấu hiệu | Chỗ đối tượng xuất hiện: tên được nhắc, khuôn mặt khớp, ảnh mẫu khớp. Dấu hiệu chưa phải nghi vấn |
| nghi vấn | Một kết quả phân tích cần rà soát; trong code và schema gọi là `finding` |

## 3. Công nghệ

| Phần | Lựa chọn | Ghi chú |
|---|---|---|
| Ngôn ngữ backend | Python 3.12 | |
| Quản lý gói | `uv` | |
| Web API | FastAPI và Pydantic v2 | C1–C5 được định nghĩa bằng mô hình Pydantic |
| Database chỉ mục | SQLite (chế độ WAL), truy cập qua SQLModel | Chỉ dùng làm chỉ mục. Hàng đợi Huey dùng file SQLite riêng |
| Tác vụ nền và lập lịch | Huey, lưu hàng đợi bằng SQLite | Không cần Redis. Hai hàng đợi: `default` và `gpu` (1 worker). Kiểm tra RSS chạy bằng periodic task |
| Thu thập | `yt-dlp` (thư viện Python), `google-api-python-client`, HTTP client cho Supadata | Phiên bản yt-dlp được ghi vào manifest. yt-dlp có thể cần thêm JS runtime (ví dụ Deno); spike T2 xác nhận |
| Media | `ffmpeg`, PySceneDetect, `imagehash` | |
| Speech-to-text | `faster-whisper` chạy trên GPU | Model chốt ở spike T3 (whisper large-v3 hoặc PhoWhisper) |
| OCR | PaddleOCR (tiếng Việt) | Nếu bản GPU xung đột với thư viện khác thì chạy bằng CPU |
| Khớp khuôn mặt | Ứng viên: InsightFace qua `onnxruntime-gpu` | Chốt model và kiểm tra giấy phép ở spike T3 |
| Khớp ảnh mẫu | Ứng viên: CLIP (`open_clip`) hoặc DINOv2, cần `torch` | Chốt ở spike T3 |
| LLM/VLM | Lớp riêng với 3 loại adapter: Anthropic SDK, OpenAI-compatible (OpenAI, DeepSeek, Qwen/DashScope, Zhipu GLM, Moonshot Kimi, OpenRouter…), Google GenAI | Tên model đặt trong file cấu hình |
| Frontend | React, Vite, TypeScript, React Router, TanStack Query, Tailwind và shadcn/ui | Giao diện tiếng Anh. Trình phát dùng thẻ `<video>` với lớp phủ tự viết |
| Chất lượng code | `ruff` (lint và format), `pytest`; `oxlint` và `tsc` cho frontend | |

Máy chạy cần WSL2 với GPU NVIDIA và CUDA, `ffmpeg` trong PATH, Node 20 trở lên. Không dùng Docker.

Rủi ro lớn nhất về cài đặt là bốn thư viện GPU (ctranslate2 cho faster-whisper, paddlepaddle-gpu, onnxruntime-gpu, torch) phải cùng chạy trong một môi trường, mỗi thư viện đòi một bộ phiên bản CUDA/cuDNN riêng. Spike T3 kiểm tra việc này trước tiên. Phương án dự phòng là chạy PaddleOCR bằng CPU, hoặc tách worker `gpu` thành nhiều môi trường riêng.

## 4. Lệnh

Lệnh backend chạy trong thư mục `backend/`. Thư mục dữ liệu lấy từ biến môi trường `H4WK_DATA_DIR`, mặc định là `data/` ở gốc repo. File cấu hình nằm ở `config/` ở gốc repo.

```bash
# Backend (trong backend/)
uv sync                                             # cài dependency
uv run h4wk init                                    # tạo data/, database chỉ mục, file cấu hình mẫu
uv run h4wk user create <username>                  # tạo tài khoản (2 người)
uv run h4wk schema export                           # xuất JSON Schema của C1–C5 vào docs/contracts/
uv run uvicorn h4wk.api.app:app --reload            # chạy API ở :8000
uv run huey_consumer h4wk.jobs.queue.huey -w 2      # worker cho hàng đợi default
uv run huey_consumer h4wk.jobs.queue.huey_gpu -w 1  # worker cho hàng đợi gpu
uv run h4wk verify <capture_dir>                    # kiểm tra toàn vẹn một bản thu
uv run h4wk reindex                                 # dựng lại database chỉ mục từ data/
uv run pytest                                       # test, không gọi mạng
uv run pytest -m live                               # test có gọi mạng/API thật, chạy tay
uv run ruff check . --fix && uv run ruff format .

# Frontend (trong web/)
npm install
npm run gen:api                                     # sinh kiểu TypeScript từ OpenAPI
npm run dev                                         # chạy ở :5173, proxy /api sang :8000
npm run build && npm run lint && npx tsc --noEmit
```

## 5. Cấu trúc thư mục

```
h4wk/
├── SPEC.md
├── docs/intent/                ← statement of intent
├── docs/contracts/             ← JSON Schema sinh từ C1–C5
├── docs/adr/                   ← ghi lại quyết định kiến trúc (ngắn)
├── backend/
│   ├── pyproject.toml
│   ├── src/h4wk/
│   │   ├── core/               ← config, db, cases, entities, auth, audit, secrets
│   │   ├── evidence/           ← capture writer, manifest, verify
│   │   ├── collectors/         ← base.py, models.py (C2), orchestrator.py, providers/{ytdlp,youtube_api,supadata}.py
│   │   ├── ai/                 ← gateway.py, providers/{anthropic,openai_compat,gemini}.py
│   │   ├── media/              ← proxy, stt, keyframes, ocr, vision, timeline.py (C3)
│   │   ├── analysis/           ← hits, static.py, faces.py, refimages.py, lexicon/, llm.py, prompts/, models.py (C4)
│   │   ├── review/             ← queue, decisions
│   │   ├── watchlist/
│   │   ├── jobs/               ← queue.py (Huey), pipeline.py
│   │   ├── api/                ← FastAPI routers, mỗi module một file
│   │   └── cli.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/           ← bản thu mẫu, raw response đã ghi sẵn, video ngắn tự quay
├── web/                        ← React app
│   └── src/{pages,components,api,lib}/
├── config/                     ← sources.toml, ai.toml, analysis.toml (không chứa secret; có bản *.example)
└── data/                       ← đã .gitignore; xem C1
```

## 6. Quy ước code

- Python có type hint đầy đủ. Dữ liệu đi qua ranh giới giữa các module luôn là mô hình Pydantic. `ruff` đặt độ dài dòng 100. Tên module, hàm và biến viết bằng tiếng Anh; comment và docstring viết bằng tiếng Việt.
- Thời gian luôn là `datetime` có múi giờ, theo giờ Việt Nam (UTC+07:00), ghi ra đĩa theo ISO-8601 kèm `+07:00`, ví dụ `2026-11-18T15:45:30+07:00`. Thời gian lấy từ nguồn ngoài (YouTube trả giờ UTC) được đổi sang giờ Việt Nam khi đọc vào. Tên thư mục bản thu có dạng `YYYYMMDDTHHMMSS`, theo giờ Việt Nam.
- Người thực hiện thao tác luôn ghi dạng `user:<username>` hoặc `system:<rule>`.
- Adapter ném đúng loại lỗi đã định nghĩa trong C2, để orchestrator biết nên thử lại hay chuyển nguồn.
- Model GPU được nạp một lần cho mỗi worker process, không nạp lại cho từng job.

```python
class YtDlpCollector(Collector):
    """Adapter yt-dlp: lấy media, phụ đề tiếng Việt, comment, thumbnail."""

    name = "ytdlp"
    capabilities = {Cap.VIDEO_METADATA, Cap.TRANSCRIPTS, Cap.COMMENTS, Cap.MEDIA, Cap.THUMBNAILS}

    def fetch(self, cap: Cap, target: VideoRef, workdir: Path) -> FetchResult:
        try:
            info = self._run(target.url, workdir, opts=self._opts_for(cap))
        except DownloadError as e:
            raise classify_ytdlp_error(e) from e  # -> Blocked | NotFound | Transient
        return FetchResult(normalized=to_normalized(info, cap), raw_files=list_files(workdir))
```

- React dùng function component. Mọi lời gọi API đi qua `web/src/api/`, với kiểu trả về sinh từ OpenAPI bằng `openapi-typescript`. Chữ trên giao diện viết bằng tiếng Anh.

## 7. Chiến lược kiểm thử

| Mức | Kiểm tra gì | Ở đâu |
|---|---|---|
| Unit | Ghi manifest, SHA-256, verify; chuyển raw sang dữ liệu chung cho từng adapter bằng raw response đã ghi sẵn (không gọi mạng); khớp tên với danh sách ví dụ đúng và phản ví dụ; kiểm tra C3, C4; tầng AI chạy với `FakeProvider` | `tests/unit` |
| Integration | Toàn luồng: thu bằng adapter giả → xử lý một video ngắn tự quay trong fixtures → `analysis` với `FakeProvider` → nghi vấn hợp lệ trong hàng đợi. Worker bị tắt giữa chừng rồi bật lại | `tests/integration` |
| Live (`-m live`) | Mỗi adapter gọi thật với 1 video; mỗi nhà cung cấp AI gọi thật 1 request | chạy tay, không bắt buộc trước khi commit |
| Demo | Checklist diễn tập 3 màn demo (T42), chạy cuối mỗi tuần từ tuần 3 | `docs/demo-checklist.md` |
| Đánh giá (làm thêm) | Bảng so sánh tĩnh và LLM trên khoảng 50 đoạn tự gán nhãn | làm nếu còn thời gian |

Không đặt ngưỡng coverage. Các phần bắt buộc có test: `evidence-store`, phần chuyển sang dữ liệu chung của từng adapter, bộ khớp tên của `analysis`, và phần kiểm tra C3/C4.

## 8. Tiêu chí thành công

Các mốc thời gian dưới đây là mục tiêu nên đạt, không phải điều kiện bắt buộc.

### Màn 1: case chuẩn bị sẵn

- [ ] Một case có ít nhất 10 video thật đã xử lý xong. Hàng đợi có ít nhất một nghi vấn từ lời nói, một từ chữ OCR và một từ hình ảnh (`visual`).
- [ ] Có ít nhất một nghi vấn từ hình ảnh nằm ở đoạn không ai nhắc tên đối tượng, được tìm ra nhờ khuôn mặt mẫu, ảnh mẫu hoặc ngữ cảnh của cả video.
- [ ] Bấm vào một nghi vấn thì video phát từ `start − 2s`. Đoạn bị nghi được tô màu trên thanh thời gian, transcript chạy theo, và khung hình hiện ra kèm khung bao của chữ OCR, khuôn mặt hoặc ảnh mẫu đã khớp.
- [ ] Thao tác Confirm, Reject (bắt buộc ghi lý do) và Needs info được ghi vào nhật ký case cùng người làm, thời điểm và lý do. Nghi vấn chỉ chuyển sang confirmed khi analyst bấm Confirm.

### Màn 2: dán link trực tiếp

- [ ] Dán link một video. Giao diện hiện tiến độ từng bước (collect → transcribe → frames → OCR/VLM → match → analyze) cho tới khi có nghi vấn.
- [ ] Mục tiêu: video dài tối đa 5 phút xử lý xong trong khoảng 5 phút.

### Màn 3: watchlist

- [ ] Một kênh tin tức trong watchlist (ví dụ HTV Tin Tức, VTV24) đăng video mới. Hệ thống tự phát hiện, tự thu và tự xử lý video đó, và video hiện trong case. Nhóm không có kênh riêng để tự đăng video, và video của kênh tin tức thường không nhắc tới đối tượng demo, nên màn 3 không yêu cầu có nghi vấn mới.
- [ ] Dòng sự kiện trên dashboard hiện `New video detected on <channel>`.
- [ ] Mục tiêu: video được xử lý xong trong khoảng 10 phút sau khi được phát hiện. Spike T2 cho thấy RSS bị cache tới 15 phút, nên lúc demo bấm nút Check now để phát hiện ngay.

### Bằng chứng

- [ ] `h4wk verify` và nút Verify integrity tính lại SHA-256 và báo OK. Sửa 1 byte trong một file thì báo FAIL đúng file đó; thiếu file thì báo `missing`; có file lạ thì báo `unexpected`.

### Nguồn thu và AI

- [ ] Tắt yt-dlp trên trang Settings thì metadata và comment vẫn thu được qua YouTube API. Manifest ghi trạng thái của mọi nguồn có thể lấy từng loại dữ liệu, kể cả nguồn bị tắt (`disabled`). Loại dữ liệu không còn nguồn nào (ví dụ video) được ghi `no_source`, và job vẫn phân tích phần văn bản.
- [ ] Khi giả lập yt-dlp bị chặn, hệ thống tự chuyển sang nguồn tiếp theo, ghi `status: "blocked"` vào manifest, và tạm ngưng yt-dlp sau 5 lần lỗi liên tiếp.
- [ ] Đổi nhà cung cấp cho tác vụ AI phân loại và cho tác vụ AI mô tả hình trên trang Settings mà không sửa code. Settings chỉ cho chọn nhà cung cấp và model, không có lựa chọn theo quốc gia, và không cho gán tác vụ mô tả hình cho model không đọc được ảnh.
- [ ] Mỗi transcript mang nhãn loại: `uploaded`, `auto`, `supadata_ai` hoặc `stt`.
- [ ] API key nhập trên giao diện được lưu ở server và không bao giờ được trả về trình duyệt; giao diện chỉ hiện giá trị đã che dạng `sk-…abcd`.

## 9. Thứ tự làm và mốc kiểm tra

| Tuần | Việc | Mốc |
|---|---|---|
| 1 | Chốt C1–C5. Chạy các spike: yt-dlp tải được trên WSL, độ trễ RSS trên kênh tin tức đăng thường xuyên, bốn thư viện GPU cùng chạy trong một môi trường. Dựng luồng tối giản chạy qua `jobs`: dán link → yt-dlp → bản thu và manifest → transcript → khớp tên tĩnh → 1 nghi vấn trên một trang đơn giản | Luồng tối giản chạy từ đầu đến cuối |
| 2–3 | YouTube API, Supadata, chuyển nguồn khi lỗi; keyframe, OCR, VLM, timeline; `ai-gateway`; LLM cho `analysis`, gồm cả comment; khớp khuôn mặt và ảnh mẫu; màn chi tiết video; hàng đợi rà soát | Màn 1 và màn 2 chạy được ở dạng thô |
| 4 | Watchlist RSS và Check now; dòng sự kiện | Ba màn demo chạy trọn |
| 5 | Giao diện Settings đầy đủ 7 mục, dashboard | Đạt toàn bộ tiêu chí ở phần 8 |
| 6 | Dữ liệu demo, diễn tập, viết báo cáo môn học | |

Checkpoint là mốc để cả nhóm kiểm tra lại, không chặn việc bắt đầu task tiếp theo.

## 10. Đặc tả từng module

### 10.1 `case-core`

Module quản lý case, đối tượng cần bảo vệ, hai tài khoản, nhật ký thao tác, cấu hình và secret.

Mỗi đối tượng có tên, biệt danh, viết tắt và hai loại ảnh mẫu: ảnh khuôn mặt (dùng cho khớp khuôn mặt) và ảnh hay bị dùng lại như ảnh chân dung quen thuộc hoặc logo (dùng cho khớp ảnh mẫu). Ảnh mẫu lưu ở `data/cases/<case>/entities/<entity_id>/refs/{face,image}/`.

`audit.log(case_id, actor, action, target, detail, status)` ghi thêm một dòng vào `data/cases/<case>/log/audit.jsonl`. Thao tác không thuộc case nào (đăng nhập, đổi Settings) ghi vào `data/log/system_audit.jsonl`. Secret nằm trong `data/secrets.json` (quyền 0600) hoặc trong `.env`, và API chỉ trả về giá trị đã che.

Hợp đồng C5 là định dạng của `config/sources.toml`, `config/ai.toml` và `config/analysis.toml`, viết bằng Pydantic. C5 nằm trong `case-core` để giao diện Settings và các module đọc cấu hình cùng dựa vào một định nghĩa.

Hạn chế được chấp nhận: tài khoản, watchlist, danh sách video đã biết và lịch sử job chỉ nằm trong database. `h4wk reindex` dựng lại case, video, bản thu, nghi vấn và quyết định rà soát từ file, nhưng làm mất các dữ liệu kể trên.

Nghiệm thu:

- Đăng nhập bằng session cookie.
- Mọi API ghi dữ liệu đều để lại một dòng nhật ký, kể cả khi thao tác thất bại.
- `h4wk reindex` dựng lại được danh sách case, video, nghi vấn và quyết định rà soát từ `data/`.

### 10.2 `evidence-store`

Hợp đồng C1 gồm cấu trúc thư mục và định dạng manifest dưới đây.

```
data/
├── log/system_audit.jsonl
└── cases/<case_id>/                     ← case_id ví dụ: 2026-11_case-0007
    ├── case.json                        ← mục tiêu, đối tượng, người phụ trách
    ├── log/audit.jsonl
    ├── entities/<entity_id>/refs/{face,image}/
    ├── channels/<channel_id>/captures/<YYYYMMDDTHHMMSS>/...
    ├── videos/<video_id>/               ← để phẳng theo video ID, không lồng dưới kênh
    │   ├── captures/<YYYYMMDDTHHMMSS>/ ← khoá chỉ đọc sau khi ghi manifest
    │   │   ├── sources/<provider>/...   ← dữ liệu thô nguyên văn
    │   │   ├── normalized.json          ← C2
    │   │   └── manifest.json
    │   └── derived/<capture_ts>/        ← tạo lại được
    │       ├── proxy_480p.mp4, audio_16k.wav, frames/, ocr.json, vision.json
    │       ├── transcripts/<kind>.<lang>.json
    │       ├── timeline.json            ← C3
    │       └── analysis/<run_id>/{hits.json,findings.json}   ← C4
    └── reviews.jsonl                    ← quyết định rà soát, chỉ ghi thêm
```

```json
// manifest.json
{
  "schema": "h4wk.manifest/1",
  "source_url": "https://www.youtube.com/watch?v=…",
  "collected_at": "2026-11-18T15:45:30+07:00",
  "collector": "user:thi | system:watchlist:w_012",
  "trigger": {"type": "manual|watchlist", "watch_item": "w_012", "event": "new_video"},
  "level": "full",
  "tool_version": "h4wk 0.1.0",
  "sources": [
    {"provider": "youtube_api", "what": "video.metadata", "status": "ok", "started_at": "…", "duration_ms": 412, "cost": {"quota_units": 1}},
    {"provider": "ytdlp", "what": "video.media", "status": "blocked", "error": "…", "version": "2026.xx.xx"},
    {"provider": "supadata", "what": "video.media", "status": "unsupported"}
  ],
  "files": {
    "normalized.json": {"sha256": "…", "bytes": 5120},
    "sources/ytdlp/video.mp4": {"sha256": "…", "bytes": 182334112}
  },
  "previous_capture": null
}
```

Giá trị `status` trong `sources`: `ok`, `failed`, `blocked`, `quota_exceeded`, `not_found`, `unsupported`, `disabled` (nguồn bị tắt trong Settings), `suspended` (nguồn đang bị tạm ngưng), `no_source` (không còn nguồn nào cho loại dữ liệu này; khi đó `provider` là `null`).

Bản thu được khoá để chống sửa nhầm: cả file lẫn thư mục được đặt chỉ đọc. Cơ chế này không chống được người cố tình sửa, và nhóm chấp nhận điều đó.

Nghiệm thu:

- Bản thu được ghi vào thư mục tạm cùng ổ đĩa, manifest ghi sau cùng, rồi `rename` sang vị trí chính thức trong một bước.
- `verify()` trả về trạng thái của từng file: OK, FAIL, missing hoặc unexpected.
- Thu lại một video tạo bản thu mới, với `previous_capture` trỏ về bản trước.

### 10.3 `collectors`

Hợp đồng C2 là mô hình dữ liệu chung viết bằng Pydantic, lưu thành `normalized.json`:

- `Video`: id, channel_id, title, description, tags, category, duration_s, published_at, view/like/comment_count, availability, is_live
- `Channel`: id, handle, title, description, country, created_at, sub/view/video_count, avatar/banner, links
- `Transcript`: kind (`uploaded|auto|supadata_ai|stt`), lang, segments[{start, end, text}]
- `Comment`: id, parent_id, author_channel_id, text, published_at, like_count
- `Thumbnail`, `MediaFile`
- `provenance`: {nhóm dữ liệu → provider}, ghi ở mức từng lần gọi nguồn
- Enum `Cap` (loại dữ liệu): `VIDEO_METADATA`, `CHANNEL_METADATA`, `CHANNEL_VIDEOS`, `PLAYLIST_VIDEOS`, `TRANSCRIPTS`, `COMMENTS`, `THUMBNAILS`, `MEDIA`
- Enum `CollectLevel` (mức thu): `metadata`, `text`, `full`, định nghĩa ở 10.7

Giao diện `Collector` gồm `name`, `capabilities: set[Cap]`, `fetch(cap, target, workdir) -> FetchResult` và `health_check() -> Health`. Lỗi chia thành năm loại: `Transient`, `Blocked`, `QuotaExceeded`, `NotFound`, `Unsupported`.

Với mỗi loại dữ liệu, orchestrator lấy từ một nguồn: thử các nguồn đang bật theo thứ tự ưu tiên của loại dữ liệu đó, nguồn sau chỉ dùng khi nguồn trước lỗi.

- Gặp `Transient` thì thử lại tối đa 3 lần rồi mới chuyển nguồn.
- Gặp `Blocked` hoặc `QuotaExceeded` thì chuyển nguồn ngay.
- Nguồn lỗi 5 lần liên tiếp (tính cả `Blocked`) bị tạm ngưng 30 phút.
- Quota YouTube API được đếm theo ngày, reset lúc nửa đêm giờ Thái Bình Dương (Pacific Time). Credit Supadata đếm theo tháng.
- Cờ `fault_injection` trong `sources.toml` cho phép giả lập một nguồn bị chặn, dùng cho test và cho demo.

Ở mức thu `full`, dữ liệu cần thu gồm metadata, phụ đề tiếng Việt (bản người đăng tải lên và bản tự động gốc, không lấy bản dịch máy), toàn bộ comment và reply, thumbnail (bản lớn nhất và `0–3.jpg`), video 720p và audio.

Nghiệm thu: thêm một adapter mới chỉ cần một file trong `providers/` và một dòng đăng ký.

### 10.4 `ai-gateway`

Module cho phép dùng nhiều nhà cung cấp LLM/VLM và đổi nhà cung cấp bằng cấu hình. Giao diện gồm hai hàm:

- `complete_structured(task, messages, schema: type[BaseModel]) -> BaseModel`
- `describe_image(task, image, prompt, schema) -> BaseModel`

`task` là tên tác vụ AI. V1 có ba tác vụ AI: `analysis.classify`, `analysis.classify_comment` và `media.vision`. Mỗi tác vụ AI được định tuyến tới một danh sách `(provider, model)` theo thứ tự ưu tiên trong `config/ai.toml`.

Mỗi cặp `(provider, model)` khai báo hai khả năng: `vision` (đọc được ảnh) và `structured` (hỗ trợ JSON schema hoặc tool calling). Cấu hình gán `media.vision` cho model không có `vision` bị từ chối ngay khi nạp.

Có ba loại adapter. `anthropic` và `gemini` dùng SDK riêng của nhà cung cấp. `openai_compat` nhận `base_url`, nên một adapter dùng chung được cho OpenAI, DeepSeek, Qwen/DashScope, GLM, Kimi và OpenRouter.

Với đầu ra có cấu trúc, adapter dùng JSON schema hoặc tool calling khi model có `structured`; nếu không thì dùng JSON mode và đặt schema trong prompt. Mọi đầu ra đều qua Pydantic validate. Đầu ra sai được gửi lại kèm thông báo lỗi, tối đa 2 lần, sau đó gateway chuyển sang nhà cung cấp tiếp theo.

Mỗi lần gọi ghi `provider`, `model`, số token, chi phí ước tính, độ trễ và trạng thái vào `data/ai_calls.jsonl`.

Nghiệm thu: sau khi đổi `analysis.classify` hoặc `media.vision` sang nhà cung cấp khác trong Settings, lần chạy tiếp theo dùng nhà cung cấp mới, và kết quả ghi đúng `provider`, `model`.

### 10.5 `media-pipeline`

Module chỉ xử lý media; mọi việc liên quan tới đối tượng của case nằm ở `analysis`. Các bước:

1. Tạo bản proxy 480p (mp4, H.264, dùng cả để phát trên trình duyệt) và audio 16 kHz một kênh.
2. Speech-to-text có mốc thời gian (`kind=stt`). Ở mức thu `full`, bước này luôn chạy, kể cả khi đã có phụ đề.
3. Tách cảnh. Trong mỗi cảnh, giải mã 2 khung mỗi giây và giữ khung khi pHash toàn khung hoặc độ khác biệt theo từng ô (lưới 4×4) vượt ngưỡng.
4. OCR trên keyframe và thumbnail, có bbox.
5. VLM mô tả keyframe và thumbnail qua tác vụ AI `media.vision`, chạy song song với số luồng giới hạn. Ngoài phần mô tả, VLM liệt kê các dấu hiệu xúc phạm nhìn thấy được (`offensive_cues`), ví dụ ảnh ghép còng tay, vẽ sừng, chữ chửi. Prompt cấm VLM đoán danh tính người trong ảnh.
6. Ghép timeline.

Các bước dùng GPU chạy trên hàng đợi `gpu`, mỗi lúc một bước.

Hợp đồng C3 là `timeline.json`:

```json
{
  "schema": "h4wk.timeline/1",
  "video_id": "…", "capture": "20261118T154530",
  "source_video_sha256": "…", "transcript_kind": "uploaded|auto|supadata_ai|stt",
  "thumbnails": [{
    "file": "thumbnails/maxres.jpg",
    "ocr": [{"text": "…", "bbox": [x, y, w, h]}],
    "visual": {"description": "…", "offensive_cues": ["…"], "provider": "…", "model": "…"}
  }],
  "segments": [{
    "id": "seg_0007", "start": 92.4, "end": 104.1,
    "speech": "…",
    "ocr": [{"frame": "frames/000231.jpg", "t": 95.0, "text": "…", "bbox": [x, y, w, h]}],
    "visual": [{"frame": "frames/000231.jpg", "t": 95.0, "description": "…", "offensive_cues": ["…"], "provider": "…", "model": "…"}]
  }]
}
```

Quy tắc ghép timeline:

- Mỗi đoạn dài khoảng 8–20 giây, gom từ các câu trong transcript chính.
- Keyframe nằm trong khoảng thời gian của đoạn nào thì gắn vào đoạn đó.
- Transcript chính được chọn theo thứ tự `uploaded > stt > auto > supadata_ai` (cấu hình được). Các transcript khác vẫn được lưu và xem được trên giao diện, nhưng không dùng để phân tích.

Nghiệm thu:

- Trong video thử nghiệm, một dòng chữ nhỏ ở góc khung chỉ hiện 1 giây vẫn được giữ lại thành keyframe và được OCR đọc.
- Một cảnh tĩnh dài 2 phút cho ra tối đa 3 keyframe.

### 10.6 `analysis`

V1 chỉ có bộ phân tích cho K1 (bôi nhọ đối tượng). Đầu vào gồm đối tượng của case cùng ảnh mẫu, timeline, tiêu đề, mô tả và comment. Việc phân tích có ba bước.

Bước 1 tìm dấu hiệu đối tượng (`hits`). Mỗi dấu hiệu ghi đối tượng, nơi tìm thấy (`via`), vị trí (đoạn, khung hình, comment), bbox và điểm số nếu có.

- Tên (`via`: `speech`, `ocr`, `title`, `description`, `comment`, `thumbnail`). Văn bản được chuẩn hoá NFC, bỏ dấu, chuyển chữ thường. Tên đầy đủ và biệt danh được so theo ranh giới từ; mỗi từ dài từ 4 ký tự trở lên được sai tối đa 1 ký tự, từ ngắn hơn phải khớp chính xác. Viết tắt phải khớp đủ ký tự theo ranh giới từ, không phân biệt hoa thường. Bỏ dấu làm một số tên trùng nhau (An và Ân); tầng LLM xử lý các trường hợp này.
- Khuôn mặt (`via: face`). Model chạy trên máy phát hiện khuôn mặt trong keyframe và thumbnail rồi so với ảnh khuôn mặt mẫu của các đối tượng trong case. Giới hạn bắt buộc: chỉ so với đối tượng của case; không đặt tên hay xác định danh tính bất kỳ người nào khác; đặc trưng của khuôn mặt không khớp không được lưu. Có thể tắt bằng `analysis.toml`.
- Ảnh mẫu (`via: ref_image`). Embedding của keyframe, thumbnail và các ô cắt theo lưới được so với embedding của ảnh mẫu, để bắt trường hợp ảnh gốc bị cắt, ghép hay đổi màu.

Một video được coi là liên quan tới đối tượng khi có ít nhất một dấu hiệu ở bất kỳ đâu.

Bước 2 là tầng tĩnh. Từ điển tiếng Việt (`analysis/lexicon/vi_insults.txt`) chạy trên các vùng văn bản có dấu hiệu tên. Từ điển chia nhóm theo danh sách thông tin xâm phạm an ninh quốc gia (xúc phạm, phỉ báng; cáo buộc không bằng chứng; xuyên tạc, bịa đặt, giả mạo; kích động, chia rẽ, bạo lực; bí mật nhà nước), mỗi nhóm gắn một `category` của C4. Có cụm từ trong từ điển thì sinh nghi vấn `analyzer: "static"` với `category` của nhóm, và `reason` ghi nhóm cùng cụm từ khớp. Dấu hiệu tên đơn thuần chỉ được ghi vào `hits.json`, không vào hàng đợi.

Bước 3 là tầng LLM, qua tác vụ AI `analysis.classify`. Các phần được gửi đi:

- đoạn có dấu hiệu (tên, khuôn mặt, ảnh mẫu), kèm một đoạn trước và một đoạn sau làm ngữ cảnh;
- trong video liên quan, mọi đoạn mà VLM ghi nhận `offensive_cues`, kể cả khi đoạn đó không nhắc tên, kèm ngữ cảnh cấp video (tiêu đề, mô tả, các dấu hiệu đã tìm được);
- tiêu đề, mô tả và thumbnail có dấu hiệu hoặc có `offensive_cues`.

Comment có dấu hiệu tên được gửi theo lô 20–50 comment qua tác vụ AI `analysis.classify_comment`.

Hợp đồng C4 gồm ba cấu trúc. Dấu hiệu (`hits.json`):

```json
{"entity": "e_01", "via": "speech|ocr|title|description|comment|thumbnail|face|ref_image",
 "segment_id": "seg_0007", "comment_id": null, "frame": "frames/000231.jpg", "bbox": [x, y, w, h], "score": 0.82}
```

Nghi vấn (`findings.json`):

```json
{
  "id": "f_…", "run_id": "…", "case_id": "…", "video_id": "…", "capture": "…",
  "analyzer": "static|llm", "analyzer_version": "0.1.0",
  "model": {"provider": "…", "model": "…"},
  "source_kind": "speech|ocr|visual|title|description|thumbnail|comment",
  "triggers": [{"via": "face", "frame": "frames/000231.jpg", "bbox": [x, y, w, h], "score": 0.82}],
  "segment_id": "seg_0007", "comment_id": null,
  "start": 92.4, "end": 104.1, "quote": "…", "frame": "frames/000231.jpg", "bbox": null,
  "entity": "e_01",
  "category": "insult|unsupported_accusation|fabrication|legitimate_criticism|neutral",
  "severity": "low|medium|high",
  "confidence": "unverified|likely|highly_likely",
  "reason": "…"
}
```

Quyết định rà soát (một dòng trong `reviews.jsonl`):

```json
{"finding_id": "f_…", "run_id": "…", "status": "confirmed|rejected|needs_info", "by": "user:thi", "at": "…", "note": "…"}
```

`id` của nghi vấn có dạng `f_<ULID>` (26 ký tự Crockford base32) và duy nhất trong cả case, vì `reviews.jsonl` ghi chung cho cả case và quyết định rà soát chỉ trỏ tới nghi vấn qua `finding_id`. Mỗi lần chạy phân tích sinh nghi vấn với `id` mới. Nghi vấn của lần chạy mới luôn bắt đầu ở trạng thái chưa rà soát, kể cả khi giống một nghi vấn đã được quyết định ở lần chạy trước. Quyết định cũ vẫn nằm trong `reviews.jsonl`, gắn với `finding_id` và `run_id` cũ.

Quy tắc:

- Nghi vấn `visual` phải trích khung hình và nêu lý do dựa trên nội dung hình.
- Nghi vấn `speech`, `ocr` và `visual` phải có `segment_id` và `start`, để bấm vào nghi vấn thì video phát từ `start − 2s`.
- Mức tin cậy viết bằng chữ, không dùng phần trăm.
- Nghi vấn là dữ liệu phái sinh. Mỗi lần chạy ghi vào một thư mục `analysis/<run_id>/` mới, nên kết quả các lần chạy trước vẫn còn nguyên.
- Nghi vấn từ comment chỉ hiển thị nội dung comment và liên kết tới comment đó. Công cụ không có màn hình hồ sơ người bình luận.

Nghiệm thu:

- Bộ khớp tên đạt toàn bộ danh sách ví dụ đúng và phản ví dụ trong test (T11).
- Đầu ra LLM sai schema không bao giờ được ghi vào `findings.json`.
- Trên video mẫu, một đoạn chỉ có ảnh chế mà không ai nhắc tên vẫn sinh nghi vấn `visual`.

### 10.7 `jobs`

Luồng xử lý gồm ba bước lớn `collect → media → analyze`. Mỗi bước lớn là một tác vụ nền của Huey, có trạng thái, tiến độ (%) và log lỗi; giao diện hiện cả các bước con. Mỗi job ghi lại người hoặc quy tắc đã kích hoạt nó.

Mức thu quyết định những gì được thu và xử lý. Mặc định là `full`, cho cả thu thủ công lẫn watchlist.

| Mức | Thu | Xử lý và phân tích |
|---|---|---|
| `metadata` | Metadata, thumbnail | Phân tích tiêu đề, mô tả |
| `text` | Thêm phụ đề tiếng Việt, comment | Thêm OCR và VLM trên thumbnail; phân tích transcript, comment |
| `full` | Thêm video 720p, audio | Toàn bộ các bước ở 10.5 và 10.6 |

Đầu vào ở màn Collect:

- Link hoặc ID video: một job.
- Link kênh hoặc `@handle`: thêm kênh vào watchlist của case (xem 10.9).
- Link playlist: mỗi video trong playlist một job, tối đa 50 video (cấu hình được).

Một video đã có bản thu trong 10 phút trước sẽ không bị thu lại, trừ khi analyst chọn buộc chạy lại.

Khi worker khởi động, job đang ở trạng thái `running` được đưa lại vào hàng đợi; nhờ các bước idempotent, job chạy tiếp từ bước dở dang.

Nghiệm thu:

- Tắt worker giữa chừng rồi bật lại thì job chạy tiếp từ bước dở dang.
- Lỗi của job hiển thị trên giao diện.

### 10.8 `review`

Hàng đợi rà soát chỉ hiện nghi vấn của lần chạy phân tích mới nhất cho mỗi bản thu. Hàng đợi sắp xếp theo mức độ, sau đó theo thời gian, và lọc được theo video, `source_kind` và trạng thái.

Màn chi tiết video gồm:

- trình phát video, phát từ bản proxy;
- transcript chạy theo thời gian, chọn được loại transcript để xem;
- thanh thời gian tô màu các đoạn bị gắn cờ;
- dải khung hình, có khung bao của chữ OCR, khuôn mặt và ảnh mẫu đã khớp;
- tab comment, đánh dấu các comment bị gắn cờ;
- lịch sử các lần thu.

Nghiệm thu: như màn 1 ở [phần 8](#8-tiêu-chí-thành-công).

### 10.9 `watchlist`

Mỗi mục watchlist là một kênh thuộc một case. V1 chỉ phát hiện sự kiện video mới.

Khi một kênh được thêm vào watchlist (từ trang Watchlist hoặc bằng cách dán link kênh ở màn Collect):

1. Hệ thống tạo một bản thu hồ sơ kênh trong `channels/<channel_id>/captures/`.
2. 10 video mới nhất (cấu hình được) được xử lý ngay ở mức thu của mục.
3. Mọi video đang có trong RSS được đánh dấu là đã biết, để lần kiểm tra sau không xử lý lại.

Một periodic task đọc RSS của từng kênh đang bật, mặc định mỗi 2 phút. Có video mới thì hệ thống tạo job theo mức thu của mục đó. Nút Check now kiểm tra ngay, dùng cả RSS lẫn uploads playlist của YouTube API. Mỗi sự kiện được ghi vào nhật ký và hiện trên dòng sự kiện ở dashboard của case.

Nghiệm thu: như màn 3 ở [phần 8](#8-tiêu-chí-thành-công).

### 10.10 `web-ui`

Các màn hình: Login, Cases, Case dashboard (kèm dòng sự kiện), Collect, Watchlist, Entities (đối tượng và ảnh mẫu), Video detail, Review queue, Capture/Evidence, Settings. Toàn bộ giao diện viết bằng tiếng Anh; nội dung tiếng Việt lấy từ YouTube giữ nguyên.

Settings gồm 7 mục:

1. Bật/tắt từng nguồn thu.
2. Nhập API key của nguồn thu (giá trị bị che).
3. Thứ tự ưu tiên giữa các nguồn trong từng loại dữ liệu, kéo thả được. Loại dữ liệu nào không còn nguồn đang bật thì hiện cảnh báo.
4. Nút Test connection cho từng nguồn.
5. Trạng thái từng nguồn (đang chạy, tạm ngưng) và quota, credit đã dùng.
6. Danh sách nhà cung cấp AI: nhập key, nhập `base_url` cho loại OpenAI-compatible, nút Test.
7. Bảng gán mỗi tác vụ AI với danh sách nhà cung cấp và model theo thứ tự ưu tiên.

Nghiệm thu: chạy được trên Chrome bản mới nhất ở độ rộng từ 1280 px trở lên. Không cần hỗ trợ màn hình điện thoại.

## 11. Ranh giới

Luôn làm:

- Chạy `pytest` và `ruff` trước khi commit.
- Dùng giờ Việt Nam và đặt tên theo ID của YouTube.
- Ghi nhật ký cho mọi thao tác, kể cả thao tác thất bại.
- Validate mọi đầu ra của LLM/VLM.
- Lưu dữ liệu thô nguyên văn.

Cần Thi đồng ý trước khi:

- Thay đổi C1–C5 sau cuối tuần 1.
- Thêm dependency nặng ngoài danh sách ở phần 3.
- Thêm module mới hoặc thay đổi phạm vi.
- Gửi một loại dữ liệu mới tới nhà cung cấp AI.

Không bao giờ:

- Commit secret hoặc thư mục `data/`.
- Trả API key về trình duyệt.
- Sửa hoặc xoá file trong `captures/` ngoài `CaptureWriter`.
- Tự động chuyển nghi vấn sang trạng thái confirmed.
- Dùng khớp khuôn mặt để xác định danh tính người không phải đối tượng của case, hoặc lưu đặc trưng của khuôn mặt không khớp.
- Gửi ảnh khuôn mặt mẫu cho nhà cung cấp AI bên ngoài; khớp khuôn mặt chỉ chạy trên máy.
- Làm màn hình hay chức năng lập hồ sơ từng người bình luận.

## 12. Ngoài phạm vi (để V2)

| Hạng mục | Lý do |
|---|---|
| Kịch bản K2, K3, K4, K5; đồ thị mạng lưới kênh | Demo chỉ cần K1 |
| Xuất báo cáo (cấu trúc chương 46 *OSINT Techniques*) | Nhóm quyết định để sau |
| Watchlist theo từ khoá, đối tượng, video, playlist | Màn 3 chỉ cần loại kênh |
| Thu lại theo lịch thưa dần; phát hiện đổi tên/avatar kênh; livestream; tự nâng mức thu | Không có trong 3 màn demo |
| Internet Archive | Không có trong 3 màn demo |
| Ảnh chụp trang và WARC | Nhóm quyết định bỏ |
| Ghi nguồn gốc tới từng trường và đánh dấu mâu thuẫn giữa các nguồn | V1 chỉ ghi ở mức từng lần gọi nguồn |
| InnerTube, Streamlink, upload file thủ công | Đã có yt-dlp, YouTube API và Supadata |
| Tìm kiếm toàn văn và ngữ nghĩa | Không có trong 3 màn demo |
| Đánh giá precision/recall chính thức | Chỉ làm bảng so sánh nhỏ nếu còn thời gian |
| Nhận diện danh tính người bất kỳ qua khuôn mặt | V1 chỉ so với đối tượng của case |

## 13. Quyết định đã chốt và việc còn treo

Việc còn treo: model cụ thể cho từng tác vụ AI, model khớp khuôn mặt và model khớp ảnh mẫu, chốt khi làm spike T3 và `ai-gateway`.

Các quyết định đã chốt:

- Mỗi loại dữ liệu lấy từ một nguồn, các nguồn khác chỉ dự phòng khi lỗi.
- Phân tích chạy trên một transcript chính; các transcript khác chỉ để xem.
- Chỉ thu phụ đề tiếng Việt: bản người đăng tải lên (`vi*`) và bản tự động gốc (`vi-orig`). Không thu bản dịch máy, vì lấy mọi ngôn ngữ kéo theo hơn 100 bản dịch và bị YouTube trả HTTP 429 (spike T2).
- Giữ mức thu, mặc định là `full`.
- Mọi thời gian trong dữ liệu, nhật ký và giao diện dùng giờ Việt Nam (UTC+07:00).
- `id` của nghi vấn là `f_<ULID>`, duy nhất trong cả case. Quyết định Reject bắt buộc có lý do, kiểm tra ngay trong hợp đồng C4.
- Phân tích lại một video thì mọi nghi vấn của lần chạy mới phải được rà soát lại; quyết định cũ không tự áp dụng.
- Comment được gửi nguyên văn cho nhà cung cấp AI, kể cả tên và ID người bình luận.
- `config/ai.toml.example` cấu hình sẵn nhiều nhà cung cấp: Anthropic, OpenAI, Gemini và các nhà OpenAI-compatible như DeepSeek, Qwen, GLM, Kimi. Settings chỉ cho chọn nhà cung cấp và model, không có lựa chọn theo quốc gia.
- Có khớp khuôn mặt, với các giới hạn ở 10.6 và phần 11. Điều này đảo ngược quy định "không nhận diện khuôn mặt" trong mô tả gốc (mục 13, 14); dữ liệu khuôn mặt là dữ liệu cá nhân nhạy cảm theo Nghị định 13/2023, nên khi demo dùng khuôn mặt của chính thành viên nhóm làm đối tượng, và báo cáo môn học giải thích lý do thay đổi.
- Nhóm không có kênh YouTube riêng. Màn 3 theo dõi kênh tin tức đăng thường xuyên, nên chỉ trình diễn việc phát hiện và tự xử lý video mới, không trình diễn nghi vấn mới.
- Thi là người chịu trách nhiệm chính và duyệt mọi thay đổi hợp đồng sau checkpoint A.
