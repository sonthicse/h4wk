"""T6: case, đối tượng, nhật ký, chỉ mục."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from h4wk.core.cases import CaseFile


def _audit(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _create(client: TestClient, title: str = "Bảo vệ ông Mẫu") -> dict:
    r = client.post("/api/cases", json={"title": title, "goal": "Theo dõi nội dung bôi nhọ"})
    assert r.status_code == 201, r.text
    return r.json()


def test_create_case_writes_case_json_and_audit(client: TestClient, data_dir: Path) -> None:
    case = _create(client)
    case_dir = data_dir / "cases" / case["id"]
    saved = CaseFile.model_validate_json((case_dir / "case.json").read_text(encoding="utf-8"))
    assert saved.title == "Bảo vệ ông Mẫu" and saved.entities == []
    lines = _audit(case_dir / "log" / "audit.jsonl")
    assert len(lines) == 1
    assert lines[0]["action"] == "case.create" and lines[0]["status"] == "ok"
    assert lines[0]["at"].endswith("+07:00")


def test_case_ids_are_sequential(client: TestClient) -> None:
    a, b = _create(client, "A"), _create(client, "B")
    assert a["id"].endswith("_case-0001") and b["id"].endswith("_case-0002")


def test_list_and_get_case(client: TestClient) -> None:
    case = _create(client)
    assert [c["id"] for c in client.get("/api/cases").json()] == [case["id"]]
    assert client.get(f"/api/cases/{case['id']}").json()["title"] == "Bảo vệ ông Mẫu"
    assert client.get("/api/cases/2026-11_case-9999").status_code == 404


def test_add_entity(client: TestClient, data_dir: Path) -> None:
    case = _create(client)
    r = client.post(
        f"/api/cases/{case['id']}/entities",
        json={"name": "Trần Văn Mẫu", "aliases": ["Mẫu Ca"], "abbreviations": ["TVM"]},
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"] == "e_01"
    got = client.get(f"/api/cases/{case['id']}").json()
    assert got["entities"][0]["aliases"] == ["Mẫu Ca"]
    lines = _audit(data_dir / "cases" / case["id"] / "log" / "audit.jsonl")
    assert [x["action"] for x in lines] == ["case.create", "entity.create"]
    assert lines[1]["target"] == "e_01"


def test_failed_write_is_audited(client: TestClient, data_dir: Path) -> None:
    r = client.post("/api/cases/2026-11_case-9999/entities", json={"name": "X"})
    assert r.status_code == 404
    lines = _audit(data_dir / "log" / "system_audit.jsonl")
    assert lines[-1]["action"] == "entity.create" and lines[-1]["status"] == "error"


def test_invalid_write_request_is_audited(client: TestClient, data_dir: Path) -> None:
    r = client.post("/api/cases", json={"goal": "thiếu title"})
    assert r.status_code == 422
    lines = _audit(data_dir / "log" / "system_audit.jsonl")
    assert lines[-1]["status"] == "error" and lines[-1]["target"] == "POST /api/cases"


def test_index_survives_restart(client: TestClient) -> None:
    case = _create(client)
    from h4wk.api.app import app

    with TestClient(app) as c2:
        assert c2.get(f"/api/cases/{case['id']}").status_code == 200
