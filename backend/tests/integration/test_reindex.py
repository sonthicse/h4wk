"""T45: h4wk reindex dựng lại chỉ mục từ file."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import PASSWORD, USERNAME
from fastapi.testclient import TestClient
from sqlmodel import Session
from typer.testing import CliRunner

from h4wk.analysis.models import Finding
from h4wk.cli import app
from h4wk.core.db import finding_row, get_engine
from h4wk.core.reindex import reindex

SAMPLE = Path(__file__).parents[1] / "fixtures" / "captures" / "h4wkDemo001"
FINDINGS = (
    SAMPLE / "derived" / "20261118T160000" / "analysis" / "r_20261118T160500" / "findings.json"
)


@pytest.fixture
def sample(client: TestClient, data_dir: Path) -> list[Finding]:
    shutil.copytree(SAMPLE, data_dir / "videos" / "h4wkDemo001")
    findings = [Finding.model_validate(f) for f in json.loads(FINDINGS.read_text("utf-8"))]
    with Session(get_engine()) as s:
        for f in findings:
            s.add(finding_row(f))
        s.commit()
    return findings


def _relogin(client: TestClient) -> None:
    r = client.post("/api/auth/login", json={"username": USERNAME, "password": PASSWORD})
    assert r.status_code == 204, r.text


def test_reindex_restores_api_after_index_deleted(client: TestClient, sample) -> None:
    assert client.post("/api/entities", json={"name": "Nguyen Van A"}).status_code in (200, 201)
    before = {u: client.get(u).json() for u in ("/api/entities", "/api/videos", "/api/findings")}
    result = reindex()
    assert result.entities == 1 and result.videos == 1 and result.findings == len(sample)
    _relogin(client)
    after = {u: client.get(u).json() for u in before}
    assert after["/api/entities"] == before["/api/entities"]
    assert after["/api/videos"] == before["/api/videos"]
    assert sorted(after["/api/findings"], key=lambda f: f["id"]) == sorted(
        before["/api/findings"], key=lambda f: f["id"]
    )


def test_reindex_restores_review_decisions(client: TestClient, sample) -> None:
    a, b = sample[0].id, sample[1].id
    post = lambda fid, body: client.post(f"/api/findings/{fid}/decision", json=body)  # noqa: E731
    assert post(a, {"status": "confirmed"}).status_code == 200
    assert post(b, {"status": "rejected", "note": "sai"}).status_code == 200
    assert post(b, {"status": "needs_info", "note": "?"}).status_code == 200

    def state() -> tuple:
        q = {i["finding"]["id"]: i["status"] for i in client.get("/api/review/queue").json()}
        h = [d["status"] for d in client.get(f"/api/findings/{b}/decisions").json()]
        return q, h

    before = state()
    reindex()
    _relogin(client)
    after = state()
    assert after == before
    assert after[1] == ["needs_info", "rejected"]


def test_reindex_skips_broken_files(client: TestClient, sample, data_dir: Path) -> None:
    run = data_dir / "videos" / "h4wkDemo001" / "derived" / "20261118T160000" / "analysis"
    (run / "r_broken").mkdir()
    (run / "r_broken" / "findings.json").write_text("{not json", encoding="utf-8")
    client.post(f"/api/findings/{sample[0].id}/decision", json={"status": "confirmed"})
    with (data_dir / "reviews.jsonl").open("a", encoding="utf-8") as f:
        f.write("rác\n\n")
    result = reindex()
    assert len(result.skipped) == 2
    assert "r_broken/findings.json" in result.skipped[0]
    assert result.skipped[1].startswith("reviews.jsonl:2:")
    assert result.findings == len(sample) and result.decisions == 1


def test_reindex_drops_accounts(client: TestClient, sample) -> None:
    reindex()
    assert client.get("/api/entities").status_code == 401


def test_cli_asks_before_deleting(data_dir: Path) -> None:
    get_engine()
    db = data_dir / "index.db"
    runner = CliRunner()
    r = runner.invoke(app, ["reindex"], input="n\n")
    assert r.exit_code != 0 and db.exists()
    r = runner.invoke(app, ["reindex", "--yes"])
    assert r.exit_code == 0, r.output
    assert "findings: 0" in r.output


def _latest_state(client: TestClient) -> list:
    return [
        client.get("/api/findings?latest_only=true").json(),
        client.get("/api/videos?latest_only=true").json(),
        client.get("/api/review/queue?latest_only=true").json(),
    ]


def test_latest_only_same_before_and_after_reindex(
    client: TestClient, sample, data_dir: Path
) -> None:
    # Bản thu B (mới hơn) phân tích ra 0 nghi vấn: latest_only không được hiện lại nghi vấn của A.
    run = data_dir / "videos" / "h4wkDemo001" / "derived" / "20261119T090000" / "analysis" / "r_b"
    run.mkdir(parents=True)
    (run / "findings.json").write_text("[]", encoding="utf-8")
    before = _latest_state(client)
    assert before[0] == [] and before[2] == []
    reindex()
    _relogin(client)
    assert _latest_state(client) == before
