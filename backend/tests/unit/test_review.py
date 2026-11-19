"""T25: hàng đợi rà soát và quyết định, dùng nghi vấn mẫu của T44."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from h4wk.analysis.models import Finding
from h4wk.core.db import FindingRow, get_engine
from h4wk.core.ids import new_ulid

SAMPLE = Path(__file__).parents[1] / "fixtures" / "captures" / "h4wkDemo001"
FINDINGS = (
    SAMPLE / "derived" / "20261118T160000" / "analysis" / "r_20261118T160500" / "findings.json"
)


def _index(findings: list[Finding]) -> None:
    with Session(get_engine()) as s:
        for f in findings:
            s.add(
                FindingRow(
                    id=f.id,
                    video_id=f.video_id,
                    capture=f.capture,
                    run_id=f.run_id,
                    data=f.model_dump_json(),
                )
            )
        s.commit()


@pytest.fixture
def sample(client: TestClient, data_dir: Path) -> list[Finding]:
    shutil.copytree(SAMPLE, data_dir / "videos" / "h4wkDemo001")
    raw = json.loads(FINDINGS.read_text(encoding="utf-8"))
    findings = [Finding.model_validate(f) for f in raw]
    _index(findings)
    return findings


def _audit(data_dir: Path) -> list[dict]:
    path = data_dir / "log" / "audit.jsonl"
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]


def test_queue_has_video_and_sorted_by_severity(client: TestClient, sample) -> None:
    items = client.get("/api/review/queue").json()
    assert len(items) == len(sample)
    assert {i["status"] for i in items} == {"unreviewed"}
    order = {"high": 0, "medium": 1, "low": 2}
    sev = [order[i["finding"]["severity"]] for i in items]
    assert sev == sorted(sev)
    assert items[0]["video"]["id"] == "h4wkDemo001" and items[0]["video"]["title"]
    assert items[0]["decisions"] == []


def test_decision_is_appended_audited_and_shown(client: TestClient, sample, data_dir: Path) -> None:
    fid = sample[0].id
    r = client.post(f"/api/findings/{fid}/decision", json={"status": "confirmed"})
    assert r.status_code == 200, r.text
    assert r.json()["by"] == "user:thi" and r.json()["at"].endswith("+07:00")
    client.post(f"/api/findings/{fid}/decision", json={"status": "needs_info", "note": "?"})
    lines = (data_dir / "reviews.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(x)["status"] for x in lines] == ["confirmed", "needs_info"]
    history = client.get(f"/api/findings/{fid}/decisions").json()
    assert [d["status"] for d in history] == ["needs_info", "confirmed"]
    item = next(i for i in client.get("/api/review/queue").json() if i["finding"]["id"] == fid)
    assert item["status"] == "needs_info"
    assert [x["action"] for x in _audit(data_dir)][-2:] == ["review.decide", "review.decide"]


def test_reject_without_note_is_422_and_not_written(
    client: TestClient, sample, data_dir: Path
) -> None:
    fid = sample[0].id
    r = client.post(f"/api/findings/{fid}/decision", json={"status": "rejected", "note": " "})
    assert r.status_code == 422
    assert not (data_dir / "reviews.jsonl").exists()
    assert _audit(data_dir)[-1]["status"] == "error"


def test_unknown_finding_is_404(client: TestClient, sample) -> None:
    r = client.post(f"/api/findings/f_{new_ulid()}/decision", json={"status": "confirmed"})
    assert r.status_code == 404


def test_filters(client: TestClient, sample) -> None:
    fid = sample[0].id
    client.post(f"/api/findings/{fid}/decision", json={"status": "rejected", "note": "sai"})
    rejected = client.get("/api/review/queue?status=rejected").json()
    assert [i["finding"]["id"] for i in rejected] == [fid]
    kind = sample[0].source_kind
    by_kind = client.get(f"/api/review/queue?source_kind={kind}").json()
    assert by_kind and {i["finding"]["source_kind"] for i in by_kind} == {kind}
    assert client.get("/api/review/queue?video=khac").json() == []


def test_new_run_starts_unreviewed_and_keeps_old_decision(
    client: TestClient, sample, data_dir: Path
) -> None:
    old = sample[0]
    client.post(f"/api/findings/{old.id}/decision", json={"status": "confirmed"})
    rerun = old.model_copy(update={"id": f"f_{new_ulid()}", "run_id": "r_20261118T170000"})
    _index([rerun])
    items = client.get("/api/review/queue").json()
    assert [i["status"] for i in items] == ["unreviewed"]
    assert items[0]["finding"]["id"] == rerun.id
    line = json.loads((data_dir / "reviews.jsonl").read_text(encoding="utf-8"))
    assert line["finding_id"] == old.id and line["run_id"] == old.run_id
