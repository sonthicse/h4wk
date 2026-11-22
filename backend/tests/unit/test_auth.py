"""Đăng nhập một tài khoản duy nhất (lấy từ .env) bằng session cookie."""

import json
from pathlib import Path

import pytest
from conftest import PASSWORD, USERNAME
from fastapi.testclient import TestClient

from h4wk.core import auth


def _lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_api_requires_login(anon_client: TestClient) -> None:
    assert anon_client.get("/api/entities").status_code == 401
    assert anon_client.post("/api/entities", json={"name": "x"}).status_code == 401
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 401


def test_login_sets_httponly_cookie_and_me(anon_client: TestClient) -> None:
    r = anon_client.post("/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 204
    assert "httponly" in r.headers["set-cookie"].lower()
    assert anon_client.get("/api/auth/me").json() == {"username": USERNAME}


def test_audit_uses_logged_in_user(client: TestClient, data_dir: Path) -> None:
    client.post("/api/entities", json={"name": "Trần Văn Mẫu"})
    line = _lines(data_dir / "log" / "audit.jsonl")[-1]
    assert line["action"] == "entity.create" and line["actor"] == f"user:{USERNAME}"


def test_wrong_password_is_rejected_and_audited(anon_client: TestClient, data_dir: Path) -> None:
    r = anon_client.post("/api/auth/login", json={"username": USERNAME, "password": "sai"})
    assert r.status_code == 401
    r = anon_client.post("/api/auth/login", json={"username": "không-có", "password": "x"})
    assert r.status_code == 401
    lines = [x for x in _lines(data_dir / "log" / "audit.jsonl") if x["action"] == "auth.login"]
    assert [x["status"] for x in lines] == ["error", "error"]
    assert "sai" not in json.dumps(lines)  # không ghi mật khẩu vào audit


def test_logout_ends_session(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/entities").status_code == 401


def test_expired_session_is_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import datetime, timedelta

    from h4wk.core import auth
    from h4wk.core.types import VN_TZ

    assert client.get("/api/entities").status_code == 200
    later = datetime.now(VN_TZ) + auth.SESSION_TTL - timedelta(minutes=1)
    monkeypatch.setattr(auth, "_now", lambda: later)
    assert client.get("/api/entities").status_code == 200  # còn 1 phút
    monkeypatch.setattr(auth, "_now", lambda: later + timedelta(minutes=2))
    assert client.get("/api/entities").status_code == 401


def test_only_the_env_account_logs_in() -> None:
    assert auth.authenticate(USERNAME, PASSWORD)
    assert not auth.authenticate(USERNAME, "sai")
    assert not auth.authenticate("khác", PASSWORD)


def test_missing_account_fails_clearly(monkeypatch: pytest.MonkeyPatch, dotenv) -> None:
    del dotenv["PASSWORD"]
    monkeypatch.setenv("PASSWORD", PASSWORD)  # biến môi trường không được tính
    with pytest.raises(RuntimeError, match="USERNAME and PASSWORD"):
        auth.account()
    from h4wk.api.app import app

    with pytest.raises(RuntimeError, match="PASSWORD"), TestClient(app):
        pass  # API không khởi động khi thiếu tài khoản


def test_os_username_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Shell có thể tự đặt USERNAME; chỉ .env được dùng."""
    monkeypatch.setenv("USERNAME", "ubuntu")
    assert auth.account() == (USERNAME, PASSWORD)


def test_password_is_not_stored(client: TestClient, data_dir: Path) -> None:
    # Chế độ WAL: dữ liệu mới có thể còn nằm trong file -wal.
    db = b"".join(p.read_bytes() for p in data_dir.glob("index.db*"))
    assert PASSWORD.encode() not in db


def test_legacy_users_table_is_dropped(data_dir: Path) -> None:
    """Index cũ có bảng users và sessions trỏ khoá ngoại tới đó: bỏ cả hai, đăng nhập vẫn chạy."""
    import sqlite3

    data_dir.mkdir(parents=True)
    con = sqlite3.connect(data_dir / "index.db")
    con.executescript(
        "CREATE TABLE users (username TEXT PRIMARY KEY, password_hash TEXT, created_at TEXT);"
        "CREATE TABLE sessions (token_hash TEXT PRIMARY KEY,"
        " username TEXT REFERENCES users(username), expires_at TEXT);"
    )
    con.close()
    token = auth.start_session(USERNAME)
    assert auth.session_user(token) == USERNAME
    con = sqlite3.connect(data_dir / "index.db")
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    assert "users" not in tables and "sessions" in tables
