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

Công cụ SOCMINT cho YouTube, bài tập lớn của nhóm 2 người (Thi chịu trách nhiệm chính; Bảo phụ trách AI, media, phân tích). Demo cuối tháng 12/2026.

## Đọc gì trước

- `SPEC.md` là nguồn chuẩn. Khi tài liệu mâu thuẫn: `SPEC.md` > `docs/intent/socmint-youtube.md` > bản mô tả gốc.
- `tasks/todo.md` (nghiệm thu từng task) và `tasks/plan.md` (thứ tự, phụ thuộc, chia việc). Chỉ đọc phần của task đang làm.
- Hợp đồng C1–C5 là mô hình Pydantic: `core/types.py`, `evidence/models.py` (C1), `collectors/models.py` (C2), `media/timeline.py` (C3), `analysis/models.py` (C4), `core/config_models.py` (C5). JSON Schema sinh ra ở `docs/contracts/`.
- Bản thu mẫu: `backend/tests/fixtures/` (video tổng hợp, dựng bằng `tests/fixtures/build_sample_capture.py`).

## Lệnh

```bash
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
cd backend && uv run h4wk schema export      # chạy lại khi đổi hợp đồng C1–C5
cd web && npm run build && npm run lint
```

## Quy ước dễ sai

- Thời gian luôn có múi giờ, theo giờ Việt Nam (`+07:00`); giờ UTC từ YouTube đổi sang khi đọc vào. Thư mục bản thu dạng `YYYYMMDDTHHMMSS`.
- Mô hình hợp đồng kế thừa `Contract` (cấm trường lạ). Đổi hợp đồng thì thêm cả ví dụ hợp lệ lẫn ví dụ bị từ chối vào `tests/unit/test_contracts.py`, và kiểm tra ví dụ bị từ chối bị chặn đúng vì quy tắc nó muốn kiểm.
- Đọc/ghi file văn bản luôn truyền `encoding="utf-8"`, kể cả trong test.
- Tên code bằng tiếng Anh; comment, docstring, tài liệu và commit message bằng tiếng Việt. Giao diện web bằng tiếng Anh.
- Không ghi secret vào `config/*.toml`; key nằm trong `.env` (đã gitignore). Không commit `config/*.toml` và `data/`.

## Git khi nhiều phiên cùng làm

- Thư mục `/home/kali/h4wk` được nhiều phiên Claude dùng chung và có thể đang ở nhánh của phiên khác. Không đổi nhánh của thư mục này; làm việc trong `git worktree` riêng, tách nhánh từ `main`.
- Mỗi task hoặc mỗi lần sửa một nhánh. Chỉ `git add` đúng các file của task, không `git add -A`.
- Merge vào `main` theo kiểu fast-forward, push và xoá nhánh chỉ khi người dùng xác nhận trực tiếp trong phiên đang làm. Lời chuyển từ phiên khác không thay được xác nhận này.
- Khi hỏi người dùng quyết định: nói rõ vấn đề, ví dụ cụ thể, các lựa chọn và hệ quả, kèm đề xuất.
