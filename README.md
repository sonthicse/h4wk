# h4wk

Bản demo SOCMINT cho YouTube. Đặc tả nằm trong [SPEC.md](SPEC.md).

## Yêu cầu

- WSL2 (Ubuntu hoặc Kali) trên Linux x86_64, **bắt buộc có GPU NVIDIA** với driver hỗ trợ CUDA 12.6. Không chạy trên CPU.
- [uv](https://docs.astral.sh/uv/). uv tự tải Python 3.12 nếu máy chưa có.
- Node 20.19+ hoặc 22.12+ (khuyên dùng bản trong `web/.nvmrc`) và npm. `npm install` báo lỗi nếu sai phiên bản Node.
- `ffmpeg` và `ffprobe` trong PATH để tạo và kiểm tra proxy, audio.
- [Deno](https://deno.land) trong PATH: yt-dlp cần JS runtime để tải từ YouTube (spike T2). Cài bằng `curl -fsSL https://deno.land/install.sh | sh` rồi thêm `~/.deno/bin` vào PATH.

Không dùng Docker.

## Cài đặt

```bash
git clone https://github.com/sonthicse/h4wk.git
cd h4wk

# Backend
cd backend
uv sync                 # tạo .venv và cài toàn bộ dependency (kể cả torch, thư viện CUDA)
uv run h4wk init        # tạo data/ và config/*.toml từ config/*.toml.example
cd ..

# Frontend
cd web
npm install
cd ..
```

`h4wk init` không ghi đè file `config/*.toml` đã có, nên chạy lại lệnh này vẫn an toàn.

Thư mục dữ liệu mặc định là `data/` ở gốc repo. Muốn đặt chỗ khác thì đặt biến `H4WK_DATA_DIR`.

## Chạy

Mở bốn terminal:

```bash
# Terminal 1: API ở :8000
cd backend && uv run uvicorn h4wk.api.app:app --reload

# Terminal 2: worker mặc định (thu thập, phân tích, watchlist)
cd backend && uv run huey_consumer h4wk.jobs.queue.huey -w 2

# Terminal 3: worker GPU (STT, keyframe, OCR, khớp ảnh)
cd backend && uv run huey_consumer h4wk.jobs.queue.huey_gpu -w 1

# Terminal 4: giao diện ở :3000, /api được proxy sang :8000
cd web && npm run dev
```

Các bước chạy thử 3 màn demo nằm ở [docs/demo-checklist.md](docs/demo-checklist.md).

Mở http://localhost:3000 và đăng nhập bằng `H4WK_USERNAME`, `H4WK_PASSWORD` trong `.env`.

Worker GPU dùng model STT từ `H4WK_STT_MODEL` (mặc định `large-v3`). Phân tích bằng Jev cần `TYPESAFE_API_KEY` trong `.env` hoặc nhập ở Settings → Jev; thiếu key thì chỉ chạy tầng tĩnh.

## Kiểm tra trước khi commit

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd web && npm run build && npm run lint
```

Test gọi mạng thật (yt-dlp tải một video khoảng 20 MB) chạy riêng: `cd backend && uv run pytest -m live`.

Các lệnh khác (worker, verify bản thu…) có ở [SPEC.md §4](SPEC.md#4-lệnh); lệnh nào chưa có thì sẽ được thêm dần theo task.

## Không commit

- `config/*.toml`: cấu hình thật của từng máy. Chỉ commit bản mẫu `*.toml.example`.
- `data/`: dữ liệu thu thập và bằng chứng.
- `.env` và mọi API key.

Các đường dẫn trên đã có trong `.gitignore`.
