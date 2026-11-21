# Spec Delta: Jev thay toàn bộ LLM và VLM

Status: approved (2026-11-21)

Kế hoạch: [tasks/plan.md](tasks/plan.md) Phase 6d (T58–T66). Bản phác giao diện: [docs/design/phase-6d/](docs/design/phase-6d/README.md).

Spec gốc: [SPEC.md](SPEC.md) §8 (Nguồn thu và AI), §10.4 `ai-gateway`, §10.5 bước 5 và hợp đồng C3, §10.6 bước 3–4, §10.10 mục 6–7, §13. Delta này thay delta cũ `SPEC-local-ai.md` (Ollama cho `media.vision` và `analysis.video_verdict`); file đó đã xoá, phần của nó đã làm và vẫn giữ được ghi ở mục "Hành vi hiện tại". Sau khi làm xong, gộp nội dung vào SPEC.md và đổi `Status` thành `implemented`.

Bản thử nghiệm: nhánh `feat/t58-jev-only` (worktree `.claude/worktrees/feat-t58-jev-only`, tách từ `feat/t56-drop-classify`). Phần backend đã sửa và backend pytest qua hết (419 test); chưa sửa web và tài liệu. Đây là tham khảo, không phải bản để merge.

## Mục tiêu

Bỏ hẳn `ai-gateway` và mọi nhà cung cấp LLM/VLM (Ollama, Gemini, OpenRouter, Anthropic). Jev là nhà cung cấp AI duy nhất: ngoài văn bản, Jev nhận thẳng keyframe và thumbnail. Kết luận theo video tính bằng quy tắc từ các nghi vấn. Mục đích: bớt một hạ tầng phải chạy (máy GPU Ollama, key cloud), bớt code phải giải thích khi demo. Đây là bài tập môn học nên chất lượng phân loại ảnh không cần cao.

Quyết định của Thi ngày 2026-11-21:

- Thay cả ba tác vụ AI: `media.vision`, `analysis.classify` (đã bỏ ở T56) và `analysis.video_verdict`.
- Bỏ hẳn mô tả ảnh: C3 không còn `visual`; giao diện không còn mục "VLM description".
- Chấp nhận đảo yêu cầu "LLM và VLM dùng được nhiều nhà cung cấp" trong [docs/intent/socmint-youtube.md](docs/intent/socmint-youtube.md) (mục 6 và phần ràng buộc). SPEC.md được ưu tiên hơn tài liệu đó.

## Kết quả thử API ngày 2026-11-21

Gọi thật `https://api.typesafe.ai/v1/systemone`, model trả về `jev-1.14.0`:

- Ảnh gửi trong `assets`: `{"<image-1>": {"type": "image", "format": "jpeg", "data_base64": "…"}}`, và `state` đổi thành danh sách `["<image-1>", …, {state cũ}]`. Thiếu header `TypeSafe-Danger-Zone-Images: true` thì API trả 400 "Images are experimental".
- Kích thước: 280×480, 400×400, 1024×320, 1280×400, 1000×1000 được nhận; 270×480, 640×200, 1600×900, 1920×1080 bị 400 "Invalid image dimensions". Keyframe video dọc của `1RUJ_6eruwA` là 270×480 nên phải phóng to.
- Mỗi ảnh khoảng 650–2900 token đầu vào tuỳ kích thước.
- Gửi 4 ảnh trong một request được.
- Chất lượng trên khung có chữ "CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ" (bộ câu hỏi R10, đối tượng thật):
  - chỉ ảnh, không có `text`: `is_attack` 0,37 rồi 0,56 ở hai lần gọi giống hệt nhau (Jev không tất định);
  - 4 keyframe của cùng đoạn: 0,59;
  - ảnh kèm dòng OCR trong `text`: 0,98, `target` đúng đối tượng.
  - Khung bình thường của cùng video: 0,01, `target: none`.
- Jev chỉ trả lời câu hỏi `choice`, `score`, `noul`; không sinh văn bản, nên không thay được mô tả ảnh hay tóm tắt kết luận.

## Hành vi hiện tại

Phần đã làm của delta cũ (T51, T52, T54, T55, T56, T57, đều đã trên `main`), chưa gộp vào SPEC.md:

- Jev dùng cấu hình R10 (`data/eval/jev/tune/final_questions.json`): `state` có `protected_targets`, `source_type`, `text`, `video_title` và ngữ cảnh theo loại (`parent_comment`; `speech_before`/`speech_after`); câu hỏi `category` (criteria `{what, examples}`), `severity`, `is_attack`, `target`. Giữ nghi vấn khi `is_attack.noul ≥ 0,5` và `target.choice ≠ "none"`. `protected_targets` và `target.criteria` sinh từ danh sách đối tượng (tên, biệt danh, viết tắt, mô tả). Trên bộ test 119 mục: P 0,754 / R 0,920.
- Jev xét mọi tiêu đề, mô tả, đoạn lời nói, đoạn có OCR hoặc mô tả ảnh, thumbnail và comment, mỗi mục một request.
- `severity` lấy từ điểm Jev 0–2: dưới 0,5 là `low`, dưới 1,5 là `medium`, còn lại `high`. `category` là danh mục vi phạm có xác suất cao nhất; `confidence` theo xác suất đó: từ 0,85 là `highly_likely`, từ 0,6 là `likely`, còn lại `unverified`. Nghi vấn tầng tĩnh luôn `medium` và `unverified`.
- T56 bỏ tác vụ `analysis.classify`; cấu hình cũ còn tuyến đó được đọc, tuyến bị bỏ qua kèm cảnh báo.
- Giao diện không hiện `reason` của nghi vấn Jev.
- Có nhà cung cấp `ollama` trong `ai-gateway`, cache mô tả ảnh theo từng ảnh (T51, T52); phần này bị xoá ở delta này.

Còn lại:

- `media.vision` mô tả mọi keyframe và thumbnail qua `ai-gateway`, ghi `vision.json` và `visual` (mô tả, `offensive_cues`, `provider`, `model`) vào `timeline.json`.
- Jev nhận văn bản của đoạn có OCR hoặc mô tả ảnh: các dòng OCR ghép với mô tả ảnh và `offensive_cues`. Đoạn có keyframe mà không có cả hai thì không gửi.
- `analysis.video_verdict` gọi LLM đọc các nghi vấn rồi trả `VideoVerdict` kèm tóm tắt tiếng Việt; LLM lỗi thì kết luận `uncertain`.
- Settings có trang AI providers (danh sách nhà cung cấp, bảng tuyến tác vụ, thẻ Jev). `config/ai.toml` theo hợp đồng C5.

## Hành vi mới

### 1. Ảnh gửi thẳng cho Jev

- Mỗi đoạn timeline có keyframe hoặc OCR là một request Jev. `text` là các dòng OCR chưa gửi ở đoạn trước, ghép bằng ` | ` (có thể rỗng). Ảnh là tối đa 4 keyframe của đoạn, lấy cách đều. `source_kind` là `ocr` khi có chữ, `visual` khi chỉ có ảnh; `frame` là khung có chữ đầu tiên, hoặc keyframe đầu tiên.
- Mỗi thumbnail là một request, gồm ảnh thumbnail và chữ OCR của nó (`source_kind: thumbnail`).
- `source_type` nói rõ ảnh và `text` là gì, ví dụ "video keyframe images; `text` is the text overlaid on them (OCR)".
- Ảnh gửi dạng JPEG chất lượng 85, thu nhỏ để cạnh dài không quá 1024 px rồi phóng to nếu cạnh ngắn dưới 320 px. Ảnh có tỉ lệ quá dài vẫn có thể bị từ chối; khi đó request lỗi được ghi như lỗi Jev khác.
- Chỉ request có ảnh mới gửi header `TypeSafe-Danger-Zone-Images: true`. Câu hỏi, ngưỡng giữ nghi vấn và cách ghi `Finding` không đổi so với T54/T55.
- Thư mục ảnh được truyền vào `jev.classify` (keyframe từ `derived/<capture>/`, thumbnail từ `captures/<capture>/`). Không có thư mục thì chỉ gửi văn bản.

### 2. Hợp đồng C3 không còn mô tả ảnh

```json
"thumbnails": [{"file": "thumbnails/maxres.jpg", "ocr": [{"text": "…", "bbox": [x, y, w, h]}]}],
"segments": [{
  "id": "seg_0007", "start": 92.4, "end": 104.1, "speech": "…",
  "frames": [{"frame": "frames/000231.jpg", "t": 95.0}],
  "ocr": [{"frame": "frames/000231.jpg", "t": 95.0, "text": "…", "bbox": [x, y, w, h]}]
}]
```

- `segments[].visual` đổi thành `frames` (chỉ `frame`, `t`); `thumbnails[].visual` bị bỏ. Mọi keyframe đều vào timeline, kể cả khung không có chữ (trước đây khung không có mô tả lẫn OCR bị bỏ).
- `t` của `frames` phải nằm trong đoạn, như `ocr`.
- `schema` vẫn là `h4wk.timeline/1`. `timeline.json` cũ trong `data/` còn `visual` vẫn đọc được: `visual` của đoạn đổi thành `frames` (giữ `frame`, `t`), `visual` của thumbnail bị bỏ, không ghi cảnh báo nào ra giao diện. Lần xử lý media sau ghi theo dạng mới.
- `vision.json` cũ để nguyên trên đĩa, không đọc nữa.

### 3. Kết luận theo video bằng quy tắc

`verdict.decide(findings, run_id, timeline)` không gọi AI:

- Không có nghi vấn vi phạm (danh mục khác `legitimate_criticism`, `neutral`) của đúng run: `violation: no`, `confidence: highly_likely`, tóm tắt "Không có nghi vấn vi phạm."
- Có ít nhất một nghi vấn vi phạm mức tin cậy `highly_likely`: `violation: yes`; còn lại `uncertain`. Nghi vấn tầng tĩnh (`unverified`) không tự đẩy kết luận lên `yes`. Thi chốt quy tắc này ngày 2026-11-21, chấp nhận nhiều video ra `yes` do precision Jev thấp (T47: 18% trên mẫu không khớp tên); người duyệt vẫn xác nhận từng video.
- `categories` xếp theo số nghi vấn giảm dần; `severity` là mức cao nhất; `confidence` là của nghi vấn xếp đầu; `finding_ids` là 10 nghi vấn đầu khi xếp theo `severity` rồi xác suất Jev (cách xếp `_rank` hiện có).
- `summary` sinh theo mẫu, ví dụ "12 nghi vấn vi phạm; danh mục: insult (8), incitement (4); mức cao nhất: high."
- `model` luôn `null`. Hợp đồng `VideoVerdict` không đổi.
- `h4wk verdict` bỏ qua run đã có `verdict.json`, trừ khi có `--force`.

### 4. Bỏ `ai-gateway`

- Xoá package `h4wk.ai`, `media/vision.py` và prompt của nó, prompt `video_verdict.md`, live test của gateway và VLM, `config/ai.toml.example`, `docs/contracts/c5-ai.json`.
- C5 bỏ `AiConfig`, `AiTask`, `ProviderConfig`, `ModelCaps`, `Route`. `config/ai.toml` của người dùng không bị xoá, chỉ không được đọc nữa.
- API bỏ `/api/settings/ai*`; giữ `/api/settings/jev*`.
- `.env.example` bỏ key LLM, thêm `TYPESAFE_API_KEY`.
- Job bỏ bước `vlm` và thông báo "images could not be described".

### 5. Giao diện

Giao diện theo bản phác Thi duyệt ngày 2026-11-21 (`docs/design/phase-6d/`).

- Settings: mục "AI providers" đổi thành "Jev" (`/settings/jev`). Thẻ API key rộng hết trang (key đã che, nhập, xoá, Test connection) và thẻ Usage (§6). Bỏ danh sách nhà cung cấp, hộp thêm nhà cung cấp, bảng tuyến tác vụ.
- Màn video: khung keyframe đang chọn bỏ "VLM description" và dấu hiệu; chỗ đó hiện "Jev findings on this frame" (nghi vấn Jev của khung hoặc đoạn chứa khung), rồi chữ OCR và ảnh mẫu đã khớp. Thẻ kết luận không hiện `model` khi `null`.
- Các bước job ở Collect bỏ `vlm`.
- Dashboard: thẻ Review (hàng đợi) và Events đổi chỗ; thẻ Usage thêm dòng Jev, mỗi nguồn ghi đã dùng, hạn mức và còn lại.
- Ngày giờ ở Videos (Latest capture) và Collect (Started) theo dạng `HH:MM dd/mm/yyyy`, giờ Việt Nam.
- Login: thẻ cao hơn, logo lớn ở trên, chữ "Sign in" dưới logo.
- Entities: dòng cảnh báo dữ liệu khuôn mặt ghi việc dùng ảnh công khai của nhân vật công chúng.

### 6. Theo dõi usage của Jev

- Mỗi request Jev ghi một dòng vào `data/jev_calls.jsonl`: thời điểm, video, bản thu, run, nguồn, số ảnh, token vào và ra, có giữ nghi vấn không, trạng thái hoặc mã lỗi, số lần thử lại vì 429. Không ghi nội dung văn bản hay ảnh.
- API tổng hợp theo kỳ (hôm nay, 7 ngày, 30 ngày) và theo nguồn, 5 lỗi gần nhất, hạn mức tháng (đã dùng, hạn mức, còn lại); API thử kết nối gọi Jev một câu ngắn.
- Hạn mức lấy từ API TypeSafe nếu có; không có thì cấu hình `jev.monthly_request_limit` trong `analysis.toml` (để trống thì không hiện hạn mức).

## Tiêu chí thành công

1. Trên video `1RUJ_6eruwA` (bản thu có sẵn, chạy lại media và phân tích với key thật), đoạn có chữ "CHÍNH QUYỀN TÔ LÂM MỚI LÀ KẺ KHỦNG BỐ" sinh nghi vấn Jev `source_kind: ocr` kèm `frame`, và request đó có ảnh.
2. Trên video mẫu `h4wkDemo001` với Jev giả: mỗi đoạn có keyframe gửi đúng đường dẫn keyframe, thumbnail gửi đúng đường dẫn thumbnail, mọi đường dẫn tồn tại; request không có ảnh không có header ảnh.
3. Ảnh 640×200 được mã hoá thành 1024×320; ảnh 270×480 có cạnh ngắn 320.
4. `timeline.json` cũ có `visual` (vd của `1RUJ_6eruwA`) đọc được, `frames` giữ đủ `frame` và `t`; màn video của video đó mở được.
5. Kết luận: test quy tắc cho `no`, `yes`, `uncertain`, thứ tự `finding_ids`, nghi vấn của run khác bị bỏ qua.
6. `grep -rn "h4wk.ai\|AiConfig\|media.vision\|video_verdict\|describe_image"` trong `backend/src`, `web/src`, `config/` không còn kết quả (trừ chỗ đọc `timeline.json` cũ).
7. Sau khi xử lý một video, `data/jev_calls.jsonl` có đúng một dòng mỗi request và không chứa nội dung văn bản; trang Jev và Dashboard hiện số khớp file đó.
8. Ảnh chụp các màn đổi khớp bản phác, Thi duyệt.
9. Backend `pytest`, `ruff check`, `ruff format --check`; web `npm run build`, `npm run lint` đều qua. Test không gọi mạng.

Không được thay đổi:

- Hợp đồng `Finding`, `VideoVerdict`, `reviews.jsonl`.
- Bộ câu hỏi R10 và ngưỡng `is_attack ≥ 0,5`.
- Jev lỗi hay thiếu key thì job vẫn xong, lỗi ghi vào `llm_error`; tầng tĩnh, khớp tên, khớp ảnh mẫu, khớp khuôn mặt vẫn chạy.
- Ảnh khuôn mặt mẫu và ảnh mẫu của đối tượng không bao giờ gửi cho Jev; chỉ gửi keyframe và thumbnail của video.

## Ranh giới (khác so với SPEC.md §11)

- Luôn: test dùng Jev giả; lời gọi Jev thật chỉ trong `pytest -m live` hoặc script đánh giá.
- Hỏi trước: đổi số ảnh tối đa mỗi request (4); gửi thêm ảnh khác ngoài keyframe và thumbnail; đổi quy tắc `yes`/`uncertain` của kết luận.
- Không: xoá `config/ai.toml`, `vision.json` hay `ai_calls.jsonl` có sẵn của người dùng.

## Ngoài phạm vi (để sau)

- Đo precision/recall của Jev trên ảnh: chỉ kiểm tiêu chí 1.
- Câu hỏi Jev riêng cho ảnh (ví dụ "ảnh có ghép còng tay không"): giữ một bộ câu hỏi R10 cho mọi nguồn.
- Cache câu trả lời Jev theo hash ảnh: Jev không tất định và chạy lại đã gửi lại văn bản như hiện nay.
- Tóm tắt kết luận bằng văn tự nhiên.
