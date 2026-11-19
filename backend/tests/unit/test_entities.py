"""T6: đối tượng, nhật ký, chỉ mục."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from h4wk.core.entities import load_entities


def _audit(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _add(client: TestClient, name: str = "Trần Văn Mẫu") -> dict:
    r = client.post(
        "/api/entities", json={"name": name, "aliases": ["Mẫu Ca"], "abbreviations": ["TVM"]}
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_add_entity_writes_entities_json_and_audit(client: TestClient, data_dir: Path) -> None:
    entity = _add(client)
    assert entity["id"] == "e_01"
    saved = load_entities()
    assert [e.name for e in saved] == ["Trần Văn Mẫu"] and saved[0].aliases == ["Mẫu Ca"]
    assert (data_dir / "entities.json").is_file()
    lines = _audit(data_dir / "log" / "audit.jsonl")
    assert lines[-1]["action"] == "entity.create" and lines[-1]["status"] == "ok"
    assert lines[-1]["target"] == "e_01"
    assert lines[-1]["at"].endswith("+07:00")


def test_entity_ids_are_sequential_and_listed(client: TestClient) -> None:
    a, b = _add(client, "A"), _add(client, "B")
    assert (a["id"], b["id"]) == ("e_01", "e_02")
    assert [e["id"] for e in client.get("/api/entities").json()] == ["e_01", "e_02"]


def test_no_entities_yet(client: TestClient) -> None:
    assert client.get("/api/entities").json() == []


def test_invalid_write_request_is_audited(client: TestClient, data_dir: Path) -> None:
    r = client.post("/api/entities", json={"aliases": ["thiếu name"]})
    assert r.status_code == 422
    lines = _audit(data_dir / "log" / "audit.jsonl")
    assert lines[-1]["status"] == "error" and lines[-1]["target"] == "POST /api/entities"


def test_index_survives_restart(client: TestClient) -> None:
    _add(client)
    from h4wk.api.app import app

    with TestClient(app, cookies=client.cookies) as c2:
        assert [e["id"] for e in c2.get("/api/entities").json()] == ["e_01"]
