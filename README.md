# h4wk

Bản demo SOCMINT cho YouTube. Đặc tả nằm trong [SPEC.md](SPEC.md), kế hoạch và danh sách task trong [tasks/](tasks/).

## Yêu cầu

- WSL2 (Ubuntu hoặc Kali). Các bước xử lý media và AI về sau cần GPU NVIDIA và CUDA.
- [uv](https://docs.astral.sh/uv/). uv tự tải Python 3.12 nếu máy chưa có.
- Node 20 trở lên và npm.
- `ffmpeg` trong PATH (yt-dlp dùng để ghép video và audio).
- [Deno](https://deno.land) trong PATH: yt-dlp cần JS runtime để tải từ YouTube (spike T2). Cài bằng `curl -fsSL https://deno.land/install.sh | sh` rồi thêm `~/.deno/bin` vào PATH.

Không dùng Docker.

## Cài đặt

```bash
git clone https://github.com/sonthicse/h4wk.git
cd h4wk

# Backend
cd backend
uv sync              # tạo .venv và cài dependency
uv run h4wk init     # tạo data/ và config/*.toml từ config/*.toml.example
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
cd backend && uv run uvicorn h4wk.api.app:app --reload

# Terminal 2: giao diện ở :5173, /api được proxy sang :8000
cd web && npm run dev
```

Mở http://localhost:5173. Trang chủ hiện `API status: ok` nghĩa là đã cài đặt đúng.

## Kiểm tra trước khi commit

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd web && npm run build && npm run lint
```

Test gọi mạng thật (yt-dlp tải một video khoảng 20 MB) chạy riêng: `cd backend && uv run pytest -m live`.

Các lệnh khác (tạo tài khoản, worker, verify bản thu…) có ở [SPEC.md §4](SPEC.md#4-lệnh); lệnh nào chưa có thì sẽ được thêm dần theo task.

## Không commit

- `config/*.toml`: cấu hình thật của từng máy. Chỉ commit bản mẫu `*.toml.example`.
- `data/`: dữ liệu thu thập và bằng chứng.
- `.env` và mọi API key.

Các đường dẫn trên đã có trong `.gitignore`.
