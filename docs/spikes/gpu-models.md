# T3 — Spike GPU và model

## Kết quả ngày 2026-11-19

- GPU quan sát được ngoài sandbox là RTX 3050 Laptop 4096 MiB, driver 610.62. Môi trường spike riêng ở `docs/spikes/gpu-env/` đã có lock cho Python 3.12, faster-whisper 1.1.1, CTranslate2 4.6.0, PaddleOCR 3.3.3, PaddlePaddle GPU 3.3.0 (cu126), ONNX Runtime GPU 1.20.0 và torch 2.6.0+cu126.
- T20 dùng worker CPU riêng với PaddleOCR 3.4.1 và PaddlePaddle 3.3.1. Bộ phát hiện dùng Apache-2.0, bộ nhận dạng tiếng Việt dùng CC BY-NC 4.0. Test nghiệm thu đã ghi trong T20 đọc đúng “LỪA ĐẢO” trên một khung. Kết quả trên 20 khung T44 ở dưới. [Model phát hiện](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det), [model nhận dạng](https://huggingface.co/meomeo163/PP-OCRv5-vi-latin-rec-v4)
- T18 dùng Whisper large-v3 làm mặc định có thể đổi qua `H4WK_STT_MODEL`. Bản thu T44 trong repo có video tổng hợp. Phép đo WER dùng bộ đọc tiếng Việt FLEURS bên dưới. Nghiệm thu transcript của video T44 vẫn chờ bản thu có lời nói.

Tệp `h4wkDemo001.mp4` được kiểm tra bằng ffprobe có video H.264 dài 40 giây và audio AAC 44,1 kHz dài 40 giây. Script tạo mẫu phát một sóng sin 440 Hz trên toàn track. Các câu tiếng Việt trong VTT phục vụ kiểm thử ưu tiên phụ đề. Chúng không phải lời nói trong track nên không dùng làm chuẩn tính WER.

Đo trên đúng video trên với OCR CPU của T20, hai luồng, weights đã có trên đĩa. Trích 20 PNG ở tốc độ 1 khung/giây, bắt đầu tại 10,5 giây. Khởi tạo bộ phát hiện và nhận dạng mất 0,91 giây, nhận dạng 20 PNG mất 5,29 giây. Cả 10 khung đầu khớp nguyên văn “TRẦN VĂN MẪU LỪA ĐẢO”. Cả 10 khung sau giữ đúng dấu của “TỘI” và “PHẠM”, trong đó 6 khung có thêm ký tự “F”. Hai cảnh có chữ lặp lại nên kết quả chỉ mô tả mẫu thử này.

**STT trên RTX 3050.** Worker backend dùng faster-whisper 1.2.1, CTranslate2 4.9.0 và Whisper large-v3 (revision `edaa852`). PyAV 19.0.2 làm bước đọc WAV lỗi ở tham số `metadata_errors`; với PyAV 16.1.0, hai lượt chạy dùng chung worker đều hoàn tất. Model nạp một lần trong 6,77 giây. Tổng thời gian mỗi lượt lần lượt là 7,07 giây (proxy đã có từ lượt chẩn đoán lỗi) và 1,70 giây (thư mục phái sinh mới). VAD loại toàn bộ 40,008 giây audio ở cả hai lượt, `segments` rỗng. Các số này đo nạp model và xử lý tín hiệu thử, chưa đo tốc độ giải mã lời nói.

**WER tiếng Việt.** Dùng tập test `vi_vn` của Google FLEURS (CC BY 4.0), sáu bản ghi đầu theo thứ tự trong `vi_vn/test/0000.parquet` có ID 1886, 1978, 1738, 1764, 1689 và 1675. Ghép nguyên câu thành WAV mono 16 kHz dài 64,68 giây. Whisper large-v3 trên cấu hình spike dùng `language="vi"`, VAD bật và kiểu tính mặc định, nạp trong 17,18 giây. Sau khi nạp, mất 12,04 giây để xử lý đoạn có nhãn. Chuẩn hóa NFC, chữ thường, bỏ dấu câu, giữ nguyên dấu tiếng Việt và tách theo khoảng trắng cho cả hai phía. Khoảng cách Levenshtein là 21 trên 150 đơn vị tham chiếu, WER **14,0%**. Kết quả này đo trên lời đọc FLEURS. [FLEURS, Conneau và cộng sự](https://huggingface.co/datasets/google/fleurs)

Trên 300 giây đầu ghép từ 25 bản ghi cùng tập test, môi trường spike trả về 72 đoạn trong **265,27 giây** sau khi đã nạp model. Tiến trình benchmark báo lỗi CUDA `invalid argument` khi thoát (mã 134), sau khi đã xuất đủ kết quả. Lượt kiểm tra bốn thư viện trong cùng tiến trình, với model STT được giải phóng trước khi chuyển sang ONNX, thoát thành công. Với phiên bản của **backend** và cùng đoạn 64,68 giây, thời gian nạp là 4,33 giây, giải mã 10,89 giây, WER **12,67%** (19/150), giải phóng model và thoát thành công.

### Kiểm tra môi trường chung và các model ảnh

Một lần `uv sync --locked --project docs/spikes/gpu-env` cài được các thư viện trong ma trận trên. Để chạy kiểm tra trên WSL, thêm các thư mục `nvidia/*/lib` trong site-packages của môi trường spike và `/usr/lib/wsl/lib` vào `LD_LIBRARY_PATH` trước khi mở Python. Nếu thiếu đường dẫn cuDNN, ONNX Runtime tự chuyển sang CPU. Trong cùng một tiến trình, torch chạy phép bình phương trên CUDA, Whisper qua CTranslate2 phiên âm đoạn FLEURS 64,68 giây thành bảy đoạn, ONNX Runtime chạy model mẫu với `CUDAExecutionProvider` và Paddle trả tensor ở `gpu:0`.

| Tác vụ | Model đã đo | Kết quả |
|---|---|---|
| OCR GPU | PP-OCRv5 mobile det và vi-latin-rec-v4 | Nạp 3,88 giây, xử lý 20 khung T44 trong 1,40 giây. Chuỗi trả về giống lần đo CPU. |
| Embedding ảnh | DINOv2 ViT-S/14, revision `ed25f3a` | Nạp 1,32 giây. Một batch gồm ảnh gốc T44 `ref_01.png`, bản cắt 10% mỗi cạnh và bản giảm độ bão hòa còn 50% mất 0,39 giây. Cosine so với ảnh gốc lần lượt 1,000, 0,906 và 0,959. |
| Khuôn mặt | Hai mạng của InsightFace buffalo_l | Nạp `det_10g.onnx` trong 1,09 giây và `w600k_r50.onnx` trong 0,22 giây, cả hai session dùng CUDAExecutionProvider. Chưa có ảnh thành viên để đánh giá chất lượng khớp. |

DINOv2 ViT-S/14 có giấy phép Apache-2.0 cho cả mã và trọng số. Lần đo embedding dùng thêm Transformers 4.49.0 trong môi trường đo riêng. Trọng số buffalo_l do InsightFace phát hành dành cho nghiên cứu phi thương mại. [DINOv2](https://github.com/facebookresearch/dinov2#license), [InsightFace](https://github.com/deepinsight/insightface#license)

## Nhật ký khảo sát ngày 2026-11-18

> Nhật ký này giữ lại để tham khảo. Kết quả đã kiểm chứng (cài chung và chạy inference) nằm ở mục "Kết quả ngày 2026-11-19" phía trên.

Ngày khảo sát: 2026-11-18. **Chưa hoàn thành**: chưa kiểm chứng cài chung hoặc chạy inference; các phiên bản dưới đây là ứng viên để thử, không phải cấu hình đã chạy được.

### Môi trường quan sát được

- Kernel `6.6.87.2-microsoft-standard-WSL2`, Ubuntu 26.04.1, x86_64; backend yêu cầu Python `>=3.12,<3.13`, và `uv python find 3.12` tìm thấy Python 3.12.
- `nvidia-smi` báo `Failed to initialize NVML: GPU access blocked by the operating system`; `/dev/dxg` không hiện diện trong môi trường thực thi. Không xác định được GPU, driver, VRAM hay compute capability. Đây là kết quả trong môi trường agent, không kết luận máy WSL của Bảo không có GPU.
- Repo hiện không có audio, transcript gán nhãn hay ảnh thử. Chưa cài các gói GPU: không thể xác thực tải thư viện, GPU hay mô hình ở đây; không thay đổi dependency backend dựa trên giả thuyết.

### Ma trận trước khi cài

| Thành phần | Ứng viên | CUDA / cuDNN theo tài liệu | Điều còn phải kiểm chứng |
|---|---|---|---|
| faster-whisper / CTranslate2 | faster-whisper + CTranslate2 bản hiện tại | CUDA 12 (cuBLAS), cuDNN 9; CT2 4.4.0 là lựa chọn CUDA 12/cuDNN 8 | Chọn và ghim phiên bản cụ thể; wheel Python 3.12; cùng process với các thư viện khác. [Nguồn](https://github.com/SYSTRAN/faster-whisper#gpu) |
| PaddlePaddle GPU / PaddleOCR | `paddlepaddle-gpu==3.3.0`, wheel `cu126` | CUDA 12.6; trang cài đặt nói wheel kèm thư viện, nhưng không nêu cụ thể phiên bản cuDNN | Wheel Python 3.12 và cuDNN thực tế, resolver và khả năng nạp chung; GPU compute capability theo yêu cầu của bản này. [Nguồn](https://www.paddlepaddle.org.cn/documentation/docs/en/install/pip/linux-pip_en.html) |
| ONNX Runtime GPU | `onnxruntime-gpu` 1.20.x | CUDA 12.x, cuDNN 9.x; tương thích PyTorch >= 2.4 với CUDA 12.x theo bảng ORT | Wheel Python 3.12 và CUDAExecutionProvider thực sự chạy; từ 1.21.x, bảng hiện hành ghi CUDA 12.8 nên không tự coi là tương thích với 12.6. [Nguồn](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) |
| PyTorch | `torch==2.6.0` bản `cu126` | Có wheel CUDA 12.6; ORT ghi PyTorch >= 2.4 dùng cuDNN 9 | Kiểm tra wheel Python 3.12, cuDNN thực tế và tương tác với Paddle. [Nguồn PyTorch](https://pytorch.org/get-started/previous-versions/), [ORT](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html) |

CUDA 12.6/cuDNN 9 là **hướng thử**, không phải chứng nhận tương thích: các wheel có thể mang phụ thuộc riêng, yêu cầu cuDNN minor khác nhau hoặc xung đột thứ tự nạp shared library. Phải kiểm tra metadata wheel, kết quả resolver và chạy tuần tự cùng process. WSL cần driver NVIDIA phía Windows và WSL 2; không cài Linux NVIDIA driver trong WSL ([NVIDIA](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)).

### Ứng viên model và giấy phép

- STT: Whisper large-v3 qua faster-whisper; PhoWhisper chỉ thử nếu chuyển đổi được. Chưa chọn chính thức, chưa đo.
- OCR: PaddleOCR với model hỗ trợ tiếng Việt; chưa xác định model và chưa đo dấu.
- Khuôn mặt: InsightFace `buffalo_l` là ứng viên, chưa thử. Mã InsightFace MIT nhưng pretrained models chỉ cho nghiên cứu phi thương mại; cần giấy phép riêng nếu thương mại ([InsightFace](https://github.com/deepinsight/insightface#license)).
- Ảnh: CLIP ViT-B/32 là ứng viên nghiên cứu, chưa thử; repo mã CLIP là MIT, nhưng chưa xác minh được giấy phép cụ thể cho weights từ model card hiện tại. Model card còn nêu surveillance và nhận diện khuôn mặt ngoài phạm vi sử dụng; cần xét tính phù hợp với ứng dụng trước khi chọn ([mã và model card](https://github.com/openai/CLIP), [model card](https://huggingface.co/openai/clip-vit-base-patch32)).

### Kết quả và việc còn lại

| Nghiệm thu | Trạng thái |
|---|---|
| Một `uv sync` cài đủ bốn thư viện, chạy tuần tự cùng process | Chưa thử |
| Thời gian nạp từng model, xử lý audio 5 phút, WER trên 1 phút có nhãn | Chưa đo |
| OCR 20 khung tiếng Việt, giữ dấu | Chưa thử |
| Ảnh thành viên, ảnh mẫu cắt/đổi màu | Chưa thử |
| Phương án Paddle CPU hoặc tách môi trường GPU | Chưa thử; chưa thể nói cài chung thất bại |

Để hoàn thành: chạy trên WSL2 có GPU được cấp vào môi trường, ghi GPU/driver/VRAM và Python 3.12; chuẩn bị audio 5 phút kèm bản chép tay 1 phút, 20 khung chữ tiếng Việt, ảnh khuôn mặt được phép dùng và ảnh mẫu biến đổi. Tạo môi trường spike cô lập, ghim đầy đủ các wheel sau khi kiểm tra metadata và index; chạy `uv sync` một lần, ghi lock và phiên bản, kiểm tra `paddle.utils.run_check()`, CUDAExecutionProvider và CUDA của torch, rồi nạp và chạy cả bốn model tuần tự trong cùng process. Ghi thời gian nạp, inference, WER (S+D+I)/N và kết quả OCR; nếu thất bại thực sự, thử và ghi phương án CPU hoặc tách môi trường. Chỉ đánh dấu T3 xong sau khi có số liệu và duyệt kết quả.

### Cập nhật kiểm tra thực tế

- Chạy `nvidia-smi` ngoài sandbox thành công: NVIDIA GeForce RTX 3050, 4096 MiB VRAM, driver 610.43.02, CUDA UMD 13.3. Lỗi ban đầu chỉ phản ánh quyền truy cập trong sandbox.
- Đã thử `uv sync` với Python 3.12.15 trong môi trường riêng tại `/tmp/h4wk-t3`, dùng wheel Paddle `cu126` và PyTorch `cu126`. Trong sandbox, DNS tới PyPI thất bại; chạy ngoài sandbox thì index chính thức của Paddle timeout. Vì resolver chưa hoàn tất, chưa có kết luận về khả năng cài chung hoặc tương thích các phiên bản; môi trường thử trong `/tmp` có thể bị xóa khi phiên kết thúc.
- 4 GB VRAM là giới hạn cần kiểm tra thực nghiệm với large-v3 và khi nạp nhiều model; chưa có số liệu để kết luận cấu hình chạy được.
