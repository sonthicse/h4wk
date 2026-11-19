# Review nhánh `feat/bao-ai-media-t10-t20`

Người review: Thi. Ngày: 2026-11-19. Commit được review: `47e51a7` (T10, T11, T16–T20).

## Kết luận

Nhánh tốt. Chạy riêng thì 142 test pass; gộp với `main` thì 235 test pass. Tên file phái sinh đúng C1, timeline, hits, findings validate được theo C3, C4, nhật ký AI ghi giờ Việt Nam.

Một số chỗ chưa thống nhất với `main`, Thi đã sửa trên nhánh `review/bao-t10-t20` (tách từ nhánh của Bảo và đã gộp `main`). Bảo chỉ cần đọc phần "Đã sửa" để biết code thay đổi ra sao, rồi làm phần "Bảo cần làm".

## Đã sửa trên nhánh `review/bao-t10-t20`

| Commit | Thay đổi | Lý do |
|---|---|---|
| `6d23f87` | Gộp `main` vào, giải xung đột `pyproject.toml` và `uv.lock` | Hai bên cùng thêm thư viện |
| `896b41a` | Bỏ mục `[keyframes]` khỏi `analysis.toml` và `AnalysisConfig`. Ngưỡng giữ khung chuyển về `KeyframeSettings` trong `media/keyframes.py`, giữ mặc định cũ (pHash 6, ô 2.0) | Hợp đồng C5 đã duyệt không có mục này; quyết định là giữ đúng C5 |
| `400249e` | `runner.analyze` nhận `core.cases.Entity` (tên, biệt danh, viết tắt) và sinh id bằng `core.ids.new_ulid` | Tránh định nghĩa đối tượng và hàm sinh ULID lần thứ hai |
| `400249e` | Từ điển chia nhóm theo danh sách thông tin xâm phạm an ninh quốc gia; mỗi nhóm gắn một category của C4; `reason` ghi nhóm và cụm từ khớp. Thêm "lừa đảo", "đồ hèn" | Bộ từ khoá phải theo danh sách này; từ điển cũ không có từ nào của bản thu mẫu T44 nên ra 0 nghi vấn |
| `400249e` | `encoding="utf-8"` cho mọi lệnh đọc/ghi trong test; `ruff format` | Quy ước trong `CLAUDE.md`; trước đó 3 test hỏng khi locale không phải UTF-8 |
| `e6b39fc` | Luồng chạy nền dùng `media.transcripts.process_capture` và `analysis.runner.analyze`; xoá `jobs/placeholder.py` | Nối T10, T11 vào T12 |
| `e6b39fc` | Đánh dấu T10, T11 xong. SPEC ghi viết tắt không phân biệt hoa thường (giữ hành vi của Bảo) | Code và test đã đạt nghiệm thu |
| `76f50e7` | C4 thêm category `incitement` (kích động, chia rẽ, bạo lực) và `state_secret` (bí mật nhà nước); từ điển gắn hai nhóm này vào category mới; JSON Schema sinh lại | Hai nhóm không khớp category nào có sẵn |

Định dạng từ điển mới (`analysis/lexicon/vi_insults.txt`): dòng `[tên nhóm: category]` mở một nhóm, các dòng sau là cụm từ. `category` phải là giá trị của C4; giá trị khác bị từ chối khi nạp. Năm nhóm gắn lần lượt `insult`, `unsupported_accusation`, `fabrication`, `incitement`, `state_secret`.

Kết quả sau khi sửa: 237 test pass ở cả locale thường lẫn `LC_ALL=C PYTHONUTF8=0`; ruff sạch. Trên bản thu mẫu T44, tầng tĩnh ra 4 nghi vấn (lời nói, hai chữ trên hình, comment).

## Bảo cần làm

1. **T3 chưa có kết quả.** T19 và T20 phụ thuộc T3 nhưng `docs/spikes/gpu-models.md` chưa có. Cần ghi: phiên bản các thư viện GPU cài chung được, model chọn cho từng việc, thời gian xử lý và nạp model, WER của STT, OCR có giữ dấu không, và giấy phép model khuôn mặt, embedding, OCR.
2. **T18** còn hai mục chưa đạt: transcript từ video mẫu thật, và nạp model một lần cho hai job. Cả hai chờ video thật của T44.
3. **T17** còn nghiệm thu live, chờ API key.
4. **T22** nối proxy, keyframe, OCR, STT, VLM vào bước media (hiện bước media mới chỉ dựng timeline từ phụ đề) và ghép OCR, VLM vào `segments` của timeline. Hàng đợi `gpu` đã có sẵn ở `jobs/queue.py`.

## Góp ý cho các lần sau

- Mỗi task một nhánh, commit nhỏ theo task. Commit `47e51a7` gộp 6 task (3.900 dòng) nên khó review và khó hoàn tác từng phần.
- Trước khi đẩy: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`; nên chạy thêm `LC_ALL=C PYTHONUTF8=0 uv run pytest`.
- Đổi hợp đồng C1–C5 (kể cả thêm mục cấu hình) thì hỏi Thi trước.
- Dùng sẵn các phần đã có trên `main`: `core.cases.Entity`, `core.ids.new_ulid`, `core.types.VN_TZ`, `core.config_models.load_toml`.

## Câu hỏi còn mở

- **Đường dẫn khung hình của thumbnail.** Với dấu hiệu `via: thumbnail`, `frame` là đường dẫn tính từ thư mục bản thu (`sources/ytdlp/maxres.jpg`), còn khung hình video tính từ thư mục phái sinh (`frames/…`). Cần thống nhất một quy ước trong C3/C4.

## Đã chốt

- C4 có thêm `incitement` và `state_secret`. Prompt của tầng LLM (T17), nếu liệt kê category bằng lời, và giao diện cần có thêm hai category này.
- Tầng tĩnh vẫn chỉ chạy ở vùng nhắc tên đối tượng. Đối tượng của case thường là lãnh đạo Đảng và Nhà nước, nên quy tắc này đủ cho K1.
