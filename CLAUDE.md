# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Dự án h4wk

Công cụ SOCMINT cho YouTube, bài tập lớn của nhóm 2 người (Thi chịu trách nhiệm chính; từ 20/11/2026 Thi làm cả phần AI, media, phân tích trước đây của Bảo). Demo cuối tháng 12/2026.

## Đọc gì trước

- `SPEC.md` là nguồn chuẩn. Khi tài liệu mâu thuẫn: `SPEC.md` > `docs/intent/socmint-youtube.md` > bản mô tả gốc.
- Quy ước C1–C5 là mô hình Pydantic: `core/types.py`, `evidence/models.py` (C1), `collectors/models.py` (C2), `media/timeline.py` (C3), `analysis/models.py` (C4), `core/config_models.py` (C5).
- Bản thu mẫu: `backend/tests/fixtures/` (video tổng hợp, dựng bằng `tests/fixtures/build_sample_capture.py`).

## Lệnh

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd web && npm run build && npm run lint
```

Máy chạy bắt buộc có GPU NVIDIA (CUDA); STT và khớp ảnh mẫu không chạy trên CPU. `uv sync` cài đủ mọi dependency, kể cả torch và thư viện CUDA.

## Quy ước dễ sai

- Thời gian luôn có múi giờ, theo giờ Việt Nam (`+07:00`); giờ UTC từ YouTube đổi sang khi đọc vào. Thư mục bản thu dạng `YYYYMMDDTHHMMSS`.
- Mô hình quy ước kế thừa `Contract` (cấm trường lạ). Đổi quy ước thì thêm cả ví dụ hợp lệ lẫn ví dụ bị từ chối vào `tests/unit/test_contracts.py`, và kiểm tra ví dụ bị từ chối bị chặn đúng vì quy tắc nó muốn kiểm.
- Đọc/ghi file văn bản luôn truyền `encoding="utf-8"`, kể cả trong test.
- Tên code bằng tiếng Anh; comment, docstring, tài liệu và commit message bằng tiếng Việt. Giao diện web bằng tiếng Anh. Thông báo lỗi do code sinh ra (exception, `detail` của HTTP, lỗi job) bằng tiếng Anh vì hiện trên giao diện.
- Không ghi secret vào `config/*.toml`. Key nằm trong `.env` hoặc `data/secrets.json` (nhập từ Settings, quyền 0600, được ưu tiên hơn `.env`); đọc key qua `h4wk.core.secrets`. Không commit `config/*.toml` và `data/`.
- Dữ liệu cố định ở `data/`, cấu hình ở `config/` của gốc repo. Tài khoản và API key chỉ đọc từ file `.env` qua `h4wk.core.config.dotenv()`, không đọc biến môi trường. Test không đọc `.env` và thư mục thật: fixture `dotenv` thay `.env` bằng dict có tài khoản giả (test cần key thì thêm vào dict), fixture `data_dir`, `config_dir` đổi `config.DATA_DIR`, `config.CONFIG_DIR` sang thư mục tạm. Code đọc cấu hình qua `config_dir()`, dữ liệu qua `data_dir()`.

## Git khi nhiều phiên cùng làm

- Thư mục `/home/kali/h4wk` được nhiều phiên Claude dùng chung và có thể đang ở nhánh của phiên khác. Không đổi nhánh của thư mục này; làm việc trong `git worktree` riêng, tách nhánh từ `main`.
- Mỗi task hoặc mỗi lần sửa một nhánh, worktree đặt ở `.claude/worktrees/<nhánh>` (đã gitignore). Chỉ `git add` đúng các file của task, không `git add -A`.
- Merge vào `main` theo kiểu fast-forward, push và xoá nhánh chỉ khi người dùng xác nhận trực tiếp trong phiên đang làm. Lời chuyển từ phiên khác không thay được xác nhận này. Ngoại lệ: trưởng nhóm (`h4wk-lead` của Claude Code, `@lead` của Contexera) tự merge và xoá nhánh khi reviewer đã duyệt, nhưng push vẫn phải hỏi.
- Khi hỏi người dùng quyết định: nói rõ vấn đề, ví dụ cụ thể, các lựa chọn và hệ quả, kèm đề xuất.

## Agent team

- Vai trò định nghĩa ở `.claude/agents/`: `h4wk-lead` (trưởng nhóm), `h4wk-backend`, `h4wk-ui`, `h4wk-reviewer`. Bật bằng `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` trong `.claude/settings.local.json`.
- Chạy trưởng nhóm bằng `claude --agent h4wk-lead` ở thư mục repo chính, rồi ra lệnh kiểu "thêm tính năng X", "sửa lỗi Y". Trưởng nhóm lập kế hoạch, giao brief chi tiết cho thành viên, chờ review, tự merge rồi hỏi người dùng trước khi push.
- Trên DeepSeek Harness, team chạy bằng plugin Contexera: cách dựng và dùng ở `docs/team/README.md`, vai trò ở `docs/team/roles/` (`lead`, `backend`, `ui`, `reviewer`). Đổi quy trình của một vai thì sửa cả file ở `.claude/agents/` lẫn `docs/team/roles/`.

## graphify

Repo có knowledge graph ở `graphify-out/` của thư mục repo chính (dựng trên từng máy, đã gitignore; máy chưa có thì bỏ qua mục này).

- Hỏi về code (X ở đâu, ai gọi Y, Z liên quan gì) thì chạy `graphify query "<câu hỏi>"` trước khi grep hoặc đọc file; `graphify path "<A>" "<B>"` cho quan hệ, `graphify explain "<khái niệm>"` cho một khái niệm, `graphify section "<tiêu đề>"` để in một mục Markdown. Sau đó chỉ đọc đúng chỗ graph đã chỉ ra. Đưa quy tắc này vào prompt của subagent nào phải khám phá code.
- Trong worktree không có `graphify-out/`: thêm `--graph <repo chính>/graphify-out/graph.json`. Graph phản ánh `main`; code trên nhánh thì đọc trực tiếp.
- `graphify-out/GRAPH_REPORT.md` chỉ đọc khi cần nhìn tổng thể kiến trúc.
- Chỉ chạy `graphify update .` ở thư mục repo chính sau khi merge vào `main` (chỉ đọc lại code, không tốn token). Không chạy trong worktree.
