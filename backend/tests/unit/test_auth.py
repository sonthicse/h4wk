"""T7: đăng nhập 2 tài khoản bằng session cookie."""

import json
from pathlib import Path

import pytest
from conftest import PASSWORD, USERNAME
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from h4wk.cli import app as cli
from h4wk.core.auth import authenticate, create_user


def _lines(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_api_requires_login(anon_client: TestClient) -> None:
    assert anon_client.get("/api/cases").status_code == 401
    assert anon_client.post("/api/cases", json={"title": "x"}).status_code == 401
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/auth/me").status_code == 401


def test_login_sets_httponly_cookie_and_me(anon_client: TestClient) -> None:
    r = anon_client.post("/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 204
    assert "httponly" in r.headers["set-cookie"].lower()
    assert anon_client.get("/api/auth/me").json() == {"username": USERNAME}


def test_audit_uses_logged_in_user(client: TestClient, data_dir: Path) -> None:
    case = client.post("/api/cases", json={"title": "Case"}).json()
    line = _lines(data_dir / "cases" / case["id"] / "log" / "audit.jsonl")[0]
    assert line["actor"] == f"user:{USERNAME}"
    assert case["owner"] == f"user:{USERNAME}"


def test_wrong_password_is_rejected_and_audited(anon_client: TestClient, data_dir: Path) -> None:
    r = anon_client.post("/api/auth/login", json={"username": USERNAME, "password": "sai"})
    assert r.status_code == 401
    r = anon_client.post("/api/auth/login", json={"username": "không-có", "password": "x"})
    assert r.status_code == 401
    lines = [
        x for x in _lines(data_dir / "log" / "system_audit.jsonl") if x["action"] == "auth.login"
    ]
    assert [x["status"] for x in lines] == ["error", "error"]
    assert "sai" not in json.dumps(lines)  # không ghi mật khẩu vào audit


def test_logout_ends_session(client: TestClient) -> None:
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/cases").status_code == 401


def test_password_is_hashed(data_dir: Path) -> None:
    create_user("bao", "bí-mật")
    # Chế độ WAL: dữ liệu mới có thể còn nằm trong file -wal.
    db = b"".join(p.read_bytes() for p in data_dir.glob("index.db*"))
    assert b"b\xc3\xad-m\xe1\xba\xadt" not in db and b"$argon2" in db
    assert authenticate("bao", "bí-mật") and not authenticate("bao", "sai")


def test_duplicate_user_rejected(data_dir: Path) -> None:
    create_user("bao", "x")
    with pytest.raises(ValueError):
        create_user("bao", "y")


def test_cli_user_create(data_dir: Path) -> None:
    r = CliRunner().invoke(cli, ["user", "create", "bao"], input="pw-123\npw-123\n")
    assert r.exit_code == 0, r.output
    assert authenticate("bao", "pw-123")
