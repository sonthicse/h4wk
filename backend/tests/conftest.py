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


@pytest.fixture(autouse=True)
def config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Test không đọc cấu hình thật của máy; thư mục cấu hình rỗng thì dùng mặc định C5."""
    d = tmp_path / "h4wk-config"
    d.mkdir()
    monkeypatch.setenv("H4WK_CONFIG_DIR", str(d))
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


@pytest.fixture(autouse=True)
def _offline_supadata_credits(request, monkeypatch):  # noqa: ANN001, ANN202
    """Không test nào hỏi /me của Supadata thật, kể cả khi máy có SUPADATA_API_KEY."""
    if "supadata_api" in request.fixturenames:
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
    CREDITS = {"native": 1, "generate": 2}

    def __init__(self) -> None:
        self.requests: list = []
        self.sleeps: list[float] = []
        self.clock = 0.0
        # khoá: "native", "generate", "job", "video", "me" → danh sách (status, body)
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
        elif path.startswith("transcript/"):
            kind = "job"
        else:
            kind = {"youtube/video": "video", "me": "me"}[path]
        defaults = {
            "native": (200, "transcript_native_vi.json"),
            "generate": (200, "job_completed.json"),
            "job": (200, "job_completed.json"),
            "video": (200, "video.json"),
            "me": (200, "me.json"),
        }
        queue = self.override.get(kind)
        if queue:  # danh sách: dùng lần lượt, phần tử cuối lặp lại mãi
            status, body = queue.pop(0) if len(queue) > 1 else queue[0]
        else:
            status, body = defaults[kind][0], self._raw(defaults[kind][1])
        credits = {"native": 1, "generate": 2, "video": 1}.get(kind, 0)
        return httpx2.Response(status, json=body, headers={"x-billable-requests": str(credits)})

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.clock += seconds

    def collector(self, key=lambda: "test-key"):  # noqa: ANN001, ANN201
        import httpx2

        from h4wk.collectors.providers.supadata import SupadataCollector

        client = httpx2.Client(transport=httpx2.MockTransport(self.handler))
        return SupadataCollector(
            client=client, key=key, sleep=self.sleep, monotonic=lambda: self.clock
        )


@pytest.fixture
def supadata_api() -> FakeSupadata:
    return FakeSupadata()
