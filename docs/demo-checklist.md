# Checklist demo

Checklist diễn tập 3 màn demo của SPEC §8 (T42). Chạy cuối mỗi tuần từ tuần 3 và cập nhật khi có tính năng mới. Người chạy tick `- [ ]` và ghi kết quả vào bảng "Lịch sử chạy" ở cuối file.

Tên trang, nút và nhãn trong các bước là chữ tiếng Anh đang hiện trên giao diện. Giờ hiển thị theo giờ Việt Nam.

## 1. Chuẩn bị máy

- [ ] **GPU.** `nvidia-smi` liệt kê GPU và phiên bản CUDA, không báo lỗi.
- [ ] **Khóa Jev.** `TYPESAFE_API_KEY` có trong `.env` hoặc nhập ở Settings → Jev.
- [ ] **Key nguồn thu.** `YOUTUBE_API_KEY`, `SUPADATA_API_KEY` có trong `.env` hoặc nhập ở Settings → Sources (key nhập ở Settings được ưu tiên). Giao diện chỉ hiện bản che của key.
- [ ] **Cài lần đầu** (đã cài rồi thì bỏ qua): `cd backend && uv sync && uv run h4wk init`, rồi `cd ../web && npm install` (từ thư mục `backend/`).


Mở 4 terminal:

- [ ] **API** (port 8000): `cd backend && uv run uvicorn h4wk.api.app:app --port 8000`
- [ ] **Worker mặc định:** `cd backend && uv run huey_consumer h4wk.jobs.queue.huey -w 2`
- [ ] **Worker GPU:** `cd backend && uv run huey_consumer h4wk.jobs.queue.huey_gpu -w 1`
- [ ] **Frontend:** `cd web && npm run dev`

Kiểm tra:

- [ ] `curl -s localhost:8000/api/health` trả HTTP 200. (Kiểm mã: `curl -s -o /dev/null -w "%{http_code}\n" localhost:8000/api/health`.)
- [ ] Mở http://localhost:3000, đăng nhập bằng `H4WK_USERNAME`, `H4WK_PASSWORD` trong `.env`. Đăng nhập xong vào thẳng **Dashboard**.

Kết quả mong đợi: cả bốn tiến trình chạy không lỗi, Dashboard mở được.

## 2. Màn 1: dữ liệu chuẩn bị sẵn

Điều kiện: đã xử lý sẵn ít nhất 10 video thật (xem trang **Videos**).

- [ ] **Videos** liệt kê ít nhất 10 video, trạng thái đã xử lý xong.
- [ ] Mở **Dashboard**: có thống kê, sự kiện gần đây và các nghi vấn nổi bật của video.
- [ ] Mở **Review queue**. Hàng đợi có ít nhất một nghi vấn từ lời nói (`speech`), một từ chữ OCR (`ocr`) và một từ hình ảnh (`visual`). Mỗi mục có nhãn loại `speech`, `ocr` hoặc `visual`.
- [ ] Có ít nhất một nghi vấn `visual` nằm ở đoạn không ai nhắc tên đối tượng, tìm ra nhờ khuôn mặt mẫu, ảnh mẫu hoặc ngữ cảnh cả video. Xem phần Reason và Triggers (`via`, `score`) ở chi tiết bên phải.

Với mỗi loại nghi vấn (speech, ocr, visual), chọn một mục rồi bấm **Open in video**:

- [ ] Video phát từ `start − 2s` (không âm).
- [ ] Đoạn bị nghi được tô màu trên thanh thời gian.
- [ ] Transcript chạy theo video.
- [ ] Khung hình hiện kèm khung bao (bbox) của chữ OCR, khuôn mặt hoặc ảnh mẫu đã khớp (với `ocr` và `visual`).

Quay lại **Review queue**, thao tác trên ba nghi vấn khác nhau:

- [ ] **Confirm** (phím `c`): trạng thái thành `confirmed`.
- [ ] **Reject** (phím `r`): bấm lần một hiện ô "Reason for rejecting (required)"; để trống thì nút **Submit reject** bị khoá. Nhập lý do rồi bấm **Submit reject** (hoặc Ctrl+Enter): trạng thái thành `rejected`.
- [ ] **Needs info** (phím `n`): trạng thái thành `needs_info`.
- [ ] Mục **Decisions** ở chi tiết nghi vấn liệt kê từng quyết định kèm người làm, thời điểm (giờ VN) và lý do.
- [ ] Nhật ký gốc: `data/reviews.jsonl` (chỉ ghi thêm) có dòng mới cho mỗi quyết định. Xem bằng `tail -n 3 data/reviews.jsonl`.
- [ ] Nghi vấn chỉ thành `confirmed` khi bấm Confirm: nghi vấn chưa thao tác vẫn là `unreviewed`.

Kết quả mong đợi: đủ ba loại nghi vấn, mỗi lần mở video phát đúng chỗ, ba thao tác đều được ghi nhận kèm người, thời điểm, lý do.

## 3. Màn 2: dán link trực tiếp

- [ ] Chọn một video dài dưới 5 phút. Mở **Collect**, mục **New collection**, dán link vào ô "Video, playlist or channel link", đặt **Level** = `full`, bấm **Collect**. Ghi lại giờ bấm.
- [ ] Bảng **Jobs** thêm một dòng của video này; cột Progress và Steps chạy lần lượt `collect → transcribe → frames → ocr → match → analyze` (job cũ hoặc job bị bỏ qua bước match vẫn có thể hiện `match` là done).
- [ ] Job kết thúc ở trạng thái xong, không lỗi. Ghi lại giờ kết thúc và số phút xử lý.
- [ ] Video mới hiện ở **Videos**; mở ra thấy transcript, khung hình và các nghi vấn (nếu video có nội dung liên quan).

Kết quả mong đợi: tiến độ từng bước hiện đúng thứ tự cho tới khi có kết quả. Mục tiêu: video tối đa 5 phút xử lý xong trong khoảng 5 phút.

## 4. Màn 3: watchlist

- [ ] Mở **Watchlist**, mục **Add channel**: nhập một kênh tin tức (ví dụ `@bbctiengviet`, hoặc HTV Tin Tức, VTV24), chọn **Level**, bấm **Add to watchlist**. Kênh hiện ở bảng **Channels**, các video mới nhất của kênh được thu ban đầu.
- [ ] **Cách A, bấm Check now:** ở dòng của kênh, bấm **Check now**. Ghi giờ bấm. Dashboard hiện sự kiện `New video detected on <kênh>`, và video mới hiện ở **Videos**. Ghi giờ video xử lý xong.
- [ ] **Cách B, chờ poll tự động:** kênh được kiểm tra RSS mỗi 2 phút; YouTube cache RSS tới 15 phút nên có thể chậm. Đo từ lúc kênh đăng video tới lúc sự kiện hiện.
- [ ] Hệ thống tự thu và tự xử lý video phát hiện được, không cần thao tác thêm.

Nhóm không có kênh riêng để đăng video, nên khi kênh chưa có video mới thì Check now không tạo sự kiện. Chọn kênh đăng thường xuyên, hoặc kiểm vào đúng lúc kênh vừa đăng. Màn 3 không yêu cầu có nghi vấn mới.

Kết quả mong đợi: sự kiện `New video detected on <kênh>` ở Dashboard, video có trong danh sách. Mục tiêu: xử lý xong trong khoảng 10 phút sau khi được phát hiện; lúc demo dùng Check now.

## 5. Bằng chứng

Bản thu nằm ở `data/videos/<video_id>/captures/<YYYYMMDDTHHMMSS>/`.

- [ ] **Trên giao diện:** mở một video ở **Videos**, tab **Captures**, mở một bản thu, bấm **Verify integrity**. Mọi file báo OK.
- [ ] **CLI trên bản thu thật:** `cd backend && uv run h4wk verify ../data/videos/<video_id>/captures/<ts>` in `OK <đường dẫn>` cho từng file, thoát mã 0.

**Chỉ thử phá trên bản sao**, không sửa `data/` thật:

```bash
T=$(mktemp -d)
cp -r data/videos/<video_id> "$T/"
chmod -R u+w "$T"                                 # bản thu gốc chỉ đọc, bản sao cần ghi được
C="$T/<video_id>/captures/<ts>"
cd backend
uv run h4wk verify "$C"                 # tất cả OK
```

- [ ] Thêm 1 byte vào một file: `printf 'x' >> "$C/normalized.json"`, chạy lại `verify` → file đó báo `FAIL`, các file khác OK, mã thoát 1.
- [ ] Xoá một file (khác file vừa sửa, vd `$C/sources/ytdlp/0.jpg`): báo `missing` đúng file đó.
- [ ] Thêm file lạ: `echo hi > "$C/lạ.txt"` → báo `unexpected` đúng file đó.
- [ ] Dọn: `rm -rf "$T"`.

Kết quả mong đợi: OK với bản thu nguyên vẹn; FAIL, `missing`, `unexpected` đúng file bị đụng tới.

## 6. Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân và cách xử lý |
| --- | --- |
| Jev báo 429 hoặc lỗi | Jev được thử lại khi 429; vẫn lỗi thì job xong với tầng tĩnh, event ghi "Jev analysis skipped". Chờ rồi chạy lại phân tích. |
| `NVIDIA GPU with CUDA is required` | Máy không có GPU NVIDIA hoặc driver không thấy GPU. Kiểm tra `nvidia-smi`; app không chạy trên CPU. |
| Thiếu thư viện Python | Chạy lại `cd backend && uv sync`. |

## 7. Lịch sử chạy

| Ngày | Người chạy | Màn | Kết quả | Ghi chú |
| --- | --- | --- | --- | --- |
| 2026-11-20 | (ví dụ) Thi | 1 | Đạt | Mẫu, xoá dòng này khi có lần chạy thật |
