import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from h4wk.analysis.models import Finding
from h4wk.collectors.providers import supadata
from h4wk.core.db import finding_row, get_engine
from h4wk.jobs import pipeline

SAMPLE = Path(__file__).parents[1] / "fixtures" / "captures" / "h4wkDemo001"
RUN = "r_20261118T160500"


@pytest.fixture
def sample(client: TestClient, data_dir: Path) -> list[Finding]:
    shutil.copytree(SAMPLE, data_dir / "videos" / "h4wkDemo001")
    path = SAMPLE / "derived" / "20261118T160000" / "analysis" / RUN / "findings.json"
    findings = [Finding.model_validate(f) for f in json.loads(path.read_text(encoding="utf-8"))]
    with Session(get_engine()) as s:
        for f in findings:
            s.add(finding_row(f))
        s.commit()
    return findings


def test_dashboard_counts_match_index(client: TestClient, sample) -> None:
    client.post(
        f"/api/findings/{sample[0].id}/decision", json={"status": "rejected", "note": "sai"}
    )
    d = client.get("/api/dashboard").json()
    assert d["video_count"] == 1 and d["capture_count"] == 1 and d["channel_count"] == 0
    assert sum(d["findings_by_severity"].values()) == len(sample)
    assert d["findings_by_status"]["rejected"] == 1
    assert d["findings_by_status"]["unreviewed"] == len(sample) - 1
    assert len(d["activity"]) == 14
    top = d["top_video"]
    assert top["id"] == "h4wkDemo001" and top["title"]
    weights = {"high": 3, "medium": 2, "low": 1}
    assert top["score"] == sum(weights[f.severity] for f in sample[1:])


def test_empty_dashboard(client: TestClient) -> None:
    d = client.get("/api/dashboard").json()
    assert d["video_count"] == 0 and d["top_video"] is None
    assert d["youtube_quota"] == {"used": 0, "limit": 10000}
    assert d["supadata_credits"] is None


def test_dashboard_shows_supadata_credits(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(supadata, "credits_usage", lambda: supadata.CreditUsage(37, 100, "Free"))
    assert client.get("/api/dashboard").json()["supadata_credits"] == {"used": 37, "limit": 100}


def test_events_have_titles_findings_error_and_review(client: TestClient, sample) -> None:
    done = pipeline.create_job("u", "h4wkDemo001", "full", False, "user:thi")
    done = pipeline._update(done.id, status="done", run_id=RUN)
    pipeline._event(done, "job_done", "x")
    failed = pipeline.create_job("u", "h4wkDemo001", "full", False, "user:thi")
    pipeline._fail(failed.id, "match", RuntimeError("no AI provider available"))
    client.post(f"/api/findings/{sample[0].id}/decision", json={"status": "confirmed"})
    ev = client.get("/api/events").json()
    assert [e["kind"] for e in ev] == ["review", "job_failed", "job_done"]
    review, fail, ok = ev
    assert ok["findings"] == len(sample) and ok["video_title"] and ok["job"]["status"] == "done"
    assert "no AI provider" in fail["error"] and fail["findings"] is None
    assert "confirmed" in review["message"] and review["video_id"] == "h4wkDemo001"
