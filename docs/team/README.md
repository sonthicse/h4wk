# Agent team h4wk trên Contexera

Team chạy bằng plugin [`@contexera/dsh-agent-team`](https://github.com/Contexera/dsh-agent-team) của DeepSeek Harness. Vai trò từng Agent nằm ở `docs/team/roles/`; Agent đọc file của mình theo dòng mô tả. Bản cho Claude Code vẫn ở `.claude/agents/`.

## Dựng team (một lần mỗi máy)

1. Mở DSH web, vào **Team mode**, chọn Workspace là thư mục repo chính (vd `/home/ubuntu/h4wk`).
2. **Agents → Add Agent**, tạo 4 Agent:

   | Name | Model | Reasoning effort | Description |
   |---|---|---|---|
   | `lead` | Claude Opus 5.5 | Medium | `Trưởng nhóm h4wk, không tự viết code, không push khi @human chưa đồng ý. Trước mọi việc, đọc docs/team/roles/lead.md và làm đúng vai đó.` |
   | `backend` | GPT-6.2-Sol | Low | `Lập trình viên backend h4wk. Trước mọi việc, đọc docs/team/roles/backend.md và làm đúng vai đó.` |
   | `ui` | Claude Sonnet 5.5 | Low | `Lập trình viên giao diện web h4wk. Trước mọi việc, đọc docs/team/roles/ui.md và làm đúng vai đó.` |
   | `reviewer` | Claude Sonnet 5.5 | Medium | `Reviewer và người nghiệm thu Task của h4wk, không sửa code. Trước mọi việc, đọc docs/team/roles/reviewer.md và làm đúng vai đó.` |

   Description chỉ ghi vai trò và trỏ tới file vai trò, không chép cả file vào: description được đưa vào ngữ cảnh mọi lượt của Agent đó và hiện trong danh sách thành viên mà Agent khác đọc qua `team_view`. Nội dung vai trò nằm trong git nên sửa và review được.

   Chỉ `lead` dùng Opus để giữ quota Claude. `ui` và `reviewer` phải dùng model đọc được ảnh (`read_image`). Hết quota thì đổi model ở **Edit Agent** rồi nhắn Agent chạy lại; đổi cho `ui`, `reviewer` thì chọn model đọc được ảnh.

3. **Projects → New Project** tên `h4wk`, chọn cả 4 Agent làm thành viên. **Edit Project → Owners**: thêm `lead`.
4. **Cài skill cho từng Agent.** Agent của DSH không thấy skill của Claude Code (plugin `agent-skills`, `~/.claude/skills`). Nó chỉ thấy skill đi kèm plugin và thư mục riêng `~/.dsh/agent-team/members/<memberId>/skills/`. Nguồn skill đã đặt ở `~/.dsh/skill-sources/`:
   - `agent-skills/`: bản clone của https://github.com/addyosmani/agent-skills (cập nhật bằng `git -C ~/.dsh/skill-sources/agent-skills pull`);
   - `playwright-cli/`: skill đi kèm `@playwright/cli`.

   Tạo xong 4 Agent và nhắn mỗi Agent một câu để nó khởi động lần đầu (lúc đó DSH mới tạo thư mục riêng), rồi chạy `python3 docs/team/install-skills.py` ở repo chính. Script tra Agent theo handle, copy đúng skill cho từng vai (danh sách ở đầu script) và chạy lại được nhiều lần. Cập nhật nguồn skill thì chạy lại. graphify không cần cài: Agent gọi thẳng CLI `graphify` qua `bash`.
5. **Trình duyệt cho `ui` và `reviewer`.** Agent không có MCP, nên điều khiển trình duyệt bằng CLI [`playwright-cli`](https://www.npmjs.com/package/@playwright/cli) (mở trang, snapshot cây phần tử, bấm, gõ, chụp ảnh rồi xem bằng `read_image`). Đã cài trên máy này:

   ```bash
   npm install -g @playwright/cli@0.1.25
   playwright-cli install-browser chromium      # vào ~/.cache/ms-playwright, không cần sudo
   ```

   Máy không có Google Chrome, nên Agent luôn mở bằng `--browser=chromium`. Thiếu thư viện hệ thống thì chạy `sudo playwright-cli install-browser chromium --with-deps`.

   Agent đăng nhập giao diện bằng tài khoản `agent` (đã tạo bằng `uv run h4wk user create agent --password ...`). Tài khoản nằm trong `~/.config/h4wk-review.env` (quyền 0600, ngoài repo):

   ```bash
   H4WK_REVIEW_USER=agent
   H4WK_REVIEW_PASSWORD=<mật khẩu>
   ```

## Dùng hằng ngày

- Ra lệnh: đăng trong Main stream của Project `h4wk`, vd `@lead thêm tính năng X` hoặc `@lead sửa lỗi Y`.
- Đổi thiết kế: mở discussion, mention `@lead` và người liên quan; chốt xong thì promote thành Task.
- Việc nhỏ đã rõ: tự mở Task, viết brief, mention người làm, đặt `reviewer` làm accountable.
- Bạn được gọi (`@human`, hiện trong Inbox) khi: push, đổi hợp đồng C1–C5 hoặc SPEC, cần làm rõ nội dung hay thay đổi, thêm thư viện, hết phase.

## Giới hạn

- Team chỉ chạy khi có sự kiện đánh thức: tin nhắn, mention, hoặc nhắc hẹn giờ (`team_reminder`) do chính Agent đặt. Task đứng im thì nhắc trong Thread. Host tắt thì không có gì chạy.
- Đồng hồ mà plugin đưa vào ngữ cảnh Agent cố định UTC+8, còn dự án dùng `+07:00`. Cần giờ thật thì chạy `TZ=Asia/Ho_Chi_Minh date`.
- Agent không có MCP. Trình duyệt đi qua `playwright-cli` (Chromium headless); xem ảnh chụp cần route model nhận được ảnh (Claude thì được).
- Agent đọc file vai trò khi bắt đầu và có thể giữ nội dung trong bộ nhớ riêng. Sửa file vai trò xong thì nhắn Agent đó đọc lại.
