"""Fixture dùng chung: mỗi test có thư mục dữ liệu riêng."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

USERNAME, PASSWORD = "thi", "mật-khẩu-thử"


@pytest.fixture(autouse=True)
def dotenv(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Thay file .env thật của máy bằng tài khoản giả. Test thêm key vào dict này
    (vd YOUTUBE_API_KEY) như sửa .env."""
    from h4wk.core import config

    values = {"USERNAME": USERNAME, "PASSWORD": PASSWORD}
    monkeypatch.setattr(config, "dotenv", lambda: dict(values))
    return values


@pytest.fixture(autouse=True)
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mỗi test một thư mục dữ liệu riêng, không đụng data/ thật."""
    from h4wk.core import config

    d = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", d)
    return d


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Test không đọc cấu hình thật của máy; thư mục cấu hình rỗng thì dùng mặc định."""
    from h4wk.core import config

    d = tmp_path / "h4wk-config"
    d.mkdir()
    monkeypatch.setattr(config, "CONFIG_DIR", d)
    return d


@pytest.fixture
def anon_client(data_dir: Path) -> Iterator[TestClient]:
    """Client chưa đăng nhập; tài khoản USERNAME lấy từ .env (giả)."""
    from h4wk.api.app import app

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


@pytest.fixture(autouse=True)
def _offline_supadata_credits(request, monkeypatch):  # noqa: ANN001, ANN202
    """Không test nào hỏi /me của Supadata thật, kể cả khi máy có SUPADATA_API_KEY."""
    if "supadata_api" in request.fixturenames or request.node.get_closest_marker("live"):
        return
    from h4wk.collectors.providers import supadata

    monkeypatch.setattr(supadata, "credits_usage", lambda *a, **k: None)


class FakeYtApi:
    """YouTube Data API giả: trả response ghi sẵn ở tests/fixtures/raw/ytapi/ theo đường dẫn."""

    RAW = Path(__file__).parent / "fixtures" / "raw" / "ytapi"

    def __init__(self) -> None:
        self.requests: list = []
        # tên endpoint → (status, body); đặt để thay response mặc định
        self.override: dict[str, tuple[int, dict]] = {}

    def _raw(self, name: str) -> dict:
        import json

        return json.loads((self.RAW / name).read_text(encoding="utf-8"))

    def handler(self, request):  # noqa: ANN001, ANN201
        import httpx2

        self.requests.append(request)
        if request.url.host == "i.ytimg.com":
            if request.url.path.endswith(("/2.jpg", "/fhddefault.jpg")):
                return httpx2.Response(404)
            return httpx2.Response(200, content=b"\xff\xd8jpg")
        endpoint = request.url.path.rsplit("/", 1)[-1]
        if endpoint in self.override:
            status, body = self.override[endpoint]
            return httpx2.Response(status, json=body)
        token = request.url.params.get("pageToken")
        names = {
            "videos": "video.json",
            "channels": "channel.json",
            "comments": "comment_replies.json",
            "commentThreads": "comment_threads.p2.json" if token else "comment_threads.p1.json",
            "playlistItems": "playlist_items.p2.json" if token else "playlist_items.p1.json",
        }
        return httpx2.Response(200, json=self._raw(names[endpoint]))

    def collector(self, key=lambda: "test-key"):  # noqa: ANN001, ANN201
        import httpx2

        from h4wk.collectors.providers.youtube_api import YouTubeApiCollector

        client = httpx2.Client(transport=httpx2.MockTransport(self.handler))
        return YouTubeApiCollector(client=client, key=key)

    def api_requests(self) -> list:
        return [r for r in self.requests if r.url.host == "www.googleapis.com"]


@pytest.fixture
def ytapi(data_dir: Path) -> FakeYtApi:
    return FakeYtApi()


class FakeSupadata:
    """Supadata giả: trả response ghi sẵn ở tests/fixtures/raw/supadata/ theo đường dẫn và mode."""

    RAW = Path(__file__).parent / "fixtures" / "raw" / "supadata"

    def __init__(self) -> None:
        self.requests: list = []
        # khoá: "native", "video", "me" → danh sách (status, body)
        self.override: dict[str, list[tuple[int, dict]]] = {}

    def _raw(self, name: str) -> dict:
        import json

        return json.loads((self.RAW / name).read_text(encoding="utf-8"))

    def handler(self, request):  # noqa: ANN001, ANN201
        import httpx2

        self.requests.append(request)
        path = request.url.path.removeprefix("/v1/")
        if path == "transcript":
            kind = request.url.params["mode"]
        else:
            kind = {"youtube/video": "video", "me": "me"}[path]
        defaults = {
            "native": (200, "transcript_native_vi.json"),
            "video": (200, "video.json"),
            "me": (200, "me.json"),
        }
        queue = self.override.get(kind)
        if queue:  # danh sách: dùng lần lượt, phần tử cuối lặp lại mãi
            status, body = queue.pop(0) if len(queue) > 1 else queue[0]
        else:
            status, body = defaults[kind][0], self._raw(defaults[kind][1])
        credits = 1 if kind == "native" else 0
        return httpx2.Response(status, json=body, headers={"x-billable-requests": str(credits)})

    def collector(self, key=lambda: "test-key"):  # noqa: ANN001, ANN201
        import httpx2

        from h4wk.collectors.providers.supadata import SupadataCollector

        client = httpx2.Client(transport=httpx2.MockTransport(self.handler))
        return SupadataCollector(client=client, key=key)


@pytest.fixture
def supadata_api() -> FakeSupadata:
    return FakeSupadata()
