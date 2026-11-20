# h4wk

Bản demo SOCMINT cho YouTube. Đặc tả nằm trong [SPEC.md](SPEC.md), kế hoạch và danh sách task trong [tasks/](tasks/).

## Yêu cầu

- WSL2 (Ubuntu hoặc Kali). Các bước xử lý media và AI về sau cần GPU NVIDIA và CUDA.
- [uv](https://docs.astral.sh/uv/). uv tự tải Python 3.12 nếu máy chưa có.
- Node 20 trở lên và npm.
- `ffmpeg` và `ffprobe` trong PATH để tạo và kiểm tra proxy, audio.
- [Deno](https://deno.land) trong PATH: yt-dlp cần JS runtime để tải từ YouTube (spike T2). Cài bằng `curl -fsSL https://deno.land/install.sh | sh` rồi thêm `~/.deno/bin` vào PATH.

Không dùng Docker.

## Cài đặt

```bash
git clone https://github.com/sonthicse/h4wk.git
cd h4wk

# Backend
cd backend
uv sync --extra stt --extra match   # tạo .venv và cài dependency, kể cả STT và khớp ảnh (cần GPU)
uv run --no-sync h4wk init     # tạo data/ và config/*.toml từ config/*.toml.example
cd ..

# Frontend
cd web
npm install
cd ..
```

`h4wk init` không ghi đè file `config/*.toml` đã có, nên chạy lại lệnh này vẫn an toàn.

Thư mục dữ liệu mặc định là `data/` ở gốc repo. Muốn đặt chỗ khác thì đặt biến `H4WK_DATA_DIR`.

## Chạy

Mở hai terminal:

```bash
# Terminal 1: API ở :8000
cd backend && uv run --no-sync uvicorn h4wk.api.app:app --reload

# Terminal 2: giao diện ở :5173, /api được proxy sang :8000
cd web && npm run dev
```

**Trong `backend/` không chạy `uv sync` hay `uv run` trơn:** lệnh đó gỡ torch và thư viện CUDA của extra. Dùng `uv run --no-sync ...`. Các bước chạy thử 3 màn demo nằm ở [docs/demo-checklist.md](docs/demo-checklist.md).

Mở http://localhost:5173. Trang chủ hiện `API status: ok` nghĩa là đã cài đặt đúng.

Job mức `full` cần worker GPU có CUDA. Trong `backend/`, chạy `uv run --extra stt --extra match huey_consumer h4wk.jobs.queue.huey_gpu -w 1`. Worker dùng model STT từ `H4WK_STT_MODEL` (mặc định `large-v3`). Extra `match` kéo theo torch, transformers và các thư viện CUDA 12.6; thiếu extra này thì bước khớp ảnh mẫu bị bỏ qua. Chỉ cài extra `stt` mà không cài `match` hoặc máy không có CUDA toolkit thì đặt `LD_LIBRARY_PATH` tới các thư mục `nvidia/*/lib` trong `.venv`. Với mức `text` hoặc `full` có ảnh, cấu hình tuyến `media.vision` trong `config/ai.toml` và khóa của nhà cung cấp trong `.env`.

## Kiểm tra trước khi commit

```bash
cd backend && uv run --no-sync pytest && uv run --no-sync ruff check . && uv run --no-sync ruff format --check .
cd web && npm run build && npm run lint
```

Test gọi mạng thật (yt-dlp tải một video khoảng 20 MB) chạy riêng: `cd backend && uv run --no-sync pytest -m live`.

Các lệnh khác (tạo tài khoản, worker, verify bản thu…) có ở [SPEC.md §4](SPEC.md#4-lệnh); lệnh nào chưa có thì sẽ được thêm dần theo task.

## Không commit

- `config/*.toml`: cấu hình thật của từng máy. Chỉ commit bản mẫu `*.toml.example`.
- `data/`: dữ liệu thu thập và bằng chứng.
- `.env` và mọi API key.

Các đường dẫn trên đã có trong `.gitignore`.
