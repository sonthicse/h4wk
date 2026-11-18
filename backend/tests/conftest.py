"""Fixture dùng chung: mỗi test có thư mục dữ liệu riêng."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

USERNAME, PASSWORD = "thi", "mật-khẩu-thử"


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "data"
    monkeypatch.setenv("H4WK_DATA_DIR", str(d))
    return d


@pytest.fixture
def anon_client(data_dir: Path) -> Iterator[TestClient]:
    """Client chưa đăng nhập; đã có sẵn tài khoản USERNAME."""
    from h4wk.api.app import app
    from h4wk.core.auth import create_user

    create_user(USERNAME, PASSWORD)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """Client đã đăng nhập bằng USERNAME."""
    r = anon_client.post("/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 204, r.text
    return anon_client


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test thường không được gọi mạng; chỉ test đánh dấu `live` mới được."""
    if request.node.get_closest_marker("live"):
        return
    import socket

    def guard(*_a: object, **_k: object) -> None:
        raise RuntimeError("test không được gọi mạng (đánh dấu @pytest.mark.live nếu cần)")

    monkeypatch.setattr(socket.socket, "connect", guard)
    monkeypatch.setattr(socket, "getaddrinfo", guard)
