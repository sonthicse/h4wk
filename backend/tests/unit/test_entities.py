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


def test_add_entity_writes_entities_toml_and_audit(
    client: TestClient, data_dir: Path, config_dir: Path
) -> None:
    entity = _add(client)
    assert entity["id"] == "e_01"
    saved = load_entities()
    assert [e.name for e in saved] == ["Trần Văn Mẫu"] and saved[0].aliases == ["Mẫu Ca"]
    assert (config_dir / "entities.toml").is_file()
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


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x01" * 32


def test_update_entity_keeps_fields_not_sent(client: TestClient, data_dir: Path) -> None:
    _add(client)
    r = client.patch("/api/entities/e_01", json={"aliases": ["Mẫu Ca", "Ông Mẫu"]})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Trần Văn Mẫu" and r.json()["abbreviations"] == ["TVM"]
    assert load_entities()[0].aliases == ["Mẫu Ca", "Ông Mẫu"]
    assert _audit(data_dir / "log" / "audit.jsonl")[-1]["action"] == "entity.update"


def test_update_unknown_entity_is_404_and_audited(client: TestClient, data_dir: Path) -> None:
    assert client.patch("/api/entities/e_99", json={"name": "X"}).status_code == 404
    line = _audit(data_dir / "log" / "audit.jsonl")[-1]
    assert line["action"] == "entity.update" and line["status"] == "error"


def test_upload_list_get_delete_ref(client: TestClient, data_dir: Path) -> None:
    _add(client)
    r = client.post("/api/entities/e_01/refs/face", content=PNG)
    assert r.status_code == 201, r.text
    ref = r.json()
    path = data_dir / "entities" / "e_01" / "refs" / "face" / ref["file"]
    assert path.read_bytes() == PNG and ref["file"].endswith(".png")
    client.post("/api/entities/e_01/refs/image", content=JPG)
    refs = client.get("/api/entities/e_01/refs").json()
    assert [x["file"] for x in refs["face"]] == [ref["file"]]
    assert [x["kind"] for x in refs["image"]] == ["image"]
    assert client.get(ref["url"]).content == PNG
    assert ref["uploaded_at"].endswith("+07:00")
    listed = client.get("/api/entities").json()[0]
    assert listed["ref_counts"] == {"face": 1, "image": 1}
    assert client.delete(ref["url"]).status_code == 204
    assert not path.exists()
    actions = [x["action"] for x in _audit(data_dir / "log" / "audit.jsonl")]
    assert actions[-3:] == ["entity.ref.add", "entity.ref.add", "entity.ref.delete"]


def test_same_image_twice_is_stored_once(client: TestClient) -> None:
    _add(client)
    a = client.post("/api/entities/e_01/refs/face", content=PNG).json()
    b = client.post("/api/entities/e_01/refs/face", content=PNG).json()
    assert a == b
    assert len(client.get("/api/entities/e_01/refs").json()["face"]) == 1


def test_non_image_is_rejected_and_audited(client: TestClient, data_dir: Path) -> None:
    _add(client)
    r = client.post("/api/entities/e_01/refs/face", content=b"<svg/>")
    assert r.status_code == 400
    line = _audit(data_dir / "log" / "audit.jsonl")[-1]
    assert line["action"] == "entity.ref.add" and line["status"] == "error"


def test_bad_kind_and_traversal_are_rejected(client: TestClient) -> None:
    _add(client)
    assert client.post("/api/entities/e_01/refs/other", content=PNG).status_code == 422
    assert client.get("/api/entities/e_01/refs/face/..%2F..%2Fentities.json").status_code == 404
    assert client.get("/api/entities/e_02/refs").status_code == 404


def test_too_large_image_is_413(client: TestClient, monkeypatch) -> None:
    from h4wk.core import entities

    monkeypatch.setattr(entities, "MAX_REF_BYTES", 16)
    _add(client)
    assert client.post("/api/entities/e_01/refs/face", content=PNG).status_code == 413


def test_create_entity_with_description(client: TestClient) -> None:
    r = client.post(
        "/api/entities", json={"name": "Tô Lâm", "description": "  General Secretary  "}
    )
    assert r.status_code == 201, r.text
    assert r.json()["description"] == "General Secretary"
    assert load_entities()[0].description == "General Secretary"


def test_patch_description_set_keep_and_clear(client: TestClient) -> None:
    _add(client)
    r = client.patch("/api/entities/e_01", json={"description": "Singer"})
    assert r.json()["description"] == "Singer"
    r = client.patch("/api/entities/e_01", json={"aliases": ["Mẫu Ca"]})
    assert r.json()["description"] == "Singer" and load_entities()[0].description == "Singer"
    r = client.patch("/api/entities/e_01", json={"description": ""})
    assert r.status_code == 200 and r.json()["description"] is None
    saved = load_entities()[0]
    assert (
        saved.description is None and saved.name == "Trần Văn Mẫu" and saved.aliases == ["Mẫu Ca"]
    )


def test_patch_null_name_is_ignored(client: TestClient) -> None:
    _add(client)
    r = client.patch("/api/entities/e_01", json={"name": None, "description": "X"})
    assert r.status_code == 200 and r.json()["name"] == "Trần Văn Mẫu"
