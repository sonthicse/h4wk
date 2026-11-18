from fastapi.testclient import TestClient

from h4wk.api.app import app


def test_health_returns_ok() -> None:
    resp = TestClient(app).get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
