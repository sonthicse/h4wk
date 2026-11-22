"""Cài skill cho từng Agent của team h4wk trên DSH.

Agent của DSH chỉ thấy skill đi kèm plugin và thư mục riêng
~/.dsh/agent-team/members/<memberId>/skills/. Script này copy skill từ
~/.dsh/skill-sources/ vào đúng thư mục của từng Agent, tra Agent theo handle
trong ledger (chỉ đọc). Chạy lại được nhiều lần; chạy sau khi tạo Agent hoặc
sau khi cập nhật nguồn skill.

Chạy: python3 docs/team/install-skills.py
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

DSH = Path.home() / ".dsh"
SOURCES = DSH / "skill-sources"
AGENT_SKILLS = SOURCES / "agent-skills"

SKILLS = {
    "lead": ["planning-and-task-breakdown", "spec-driven-development", "interview-me"],
    "backend": [
        "incremental-implementation",
        "test-driven-development",
        "debugging-and-error-recovery",
        "api-and-interface-design",
    ],
    "ui": [
        "incremental-implementation",
        "test-driven-development",
        "debugging-and-error-recovery",
        "frontend-ui-engineering",
        "playwright-cli",
    ],
    "reviewer": ["playwright-cli"],
}


def members_by_handle() -> dict[str, str]:
    """Đọc ledger (chỉ đọc) để lấy memberId theo handle mới nhất."""
    db = sqlite3.connect(f"file:{DSH / 'storages' / 'agent_team.sqlite'}?mode=ro", uri=True)
    rows = db.execute("select value from u_agent_team_operations").fetchall()
    ops = sorted((json.loads(v) for (v,) in rows), key=lambda o: o["sequence"])
    found: dict[str, str] = {}
    for op in ops:
        if op["kind"] in ("team/member-added", "team/member-updated"):
            member = op["data"]["member"]
            found = {h: m for h, m in found.items() if m != member["memberId"]}
            found[member["handle"].lower()] = member["memberId"]
    return found


def source_of(skill: str) -> Path:
    if skill == "playwright-cli":
        return SOURCES / "playwright-cli"
    return AGENT_SKILLS / "skills" / skill


def main() -> int:
    members = members_by_handle()
    missing = False
    for handle, skills in SKILLS.items():
        member_id = members.get(handle)
        root = DSH / "agent-team" / "members" / (member_id or "").replace(":", "-")
        if not member_id or not root.is_dir():
            print(f"[bỏ qua] chưa có Agent '{handle}' hoặc chưa kích hoạt lần nào")
            missing = True
            continue
        for skill in skills:
            dest = root / "skills" / skill
            shutil.rmtree(dest, ignore_errors=True)
            shutil.copytree(source_of(skill), dest)
        if any(s != "playwright-cli" for s in skills):
            shutil.rmtree(root / "references", ignore_errors=True)
            shutil.copytree(AGENT_SKILLS / "references", root / "references")
        print(f"[xong] {handle}: {', '.join(skills)}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
