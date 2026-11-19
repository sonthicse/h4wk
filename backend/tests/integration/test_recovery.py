"""T46: chạy lại job bị treo khi consumer khởi động."""
# ruff: noqa: F811

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pipeline_fixtures import VIDEO, SampleCollector, _immediate, fake_source  # noqa: F401
from sqlmodel import Session

from h4wk.collectors.models import Cap
from h4wk.core.db import JobRow, get_engine
from h4wk.jobs import pipeline, recovery
from h4wk.media import ocr

pytestmark = pytest.mark.usefixtures("fake_source")


def _job(job_id: str) -> JobRow:
    with Session(get_engine()) as s:
        row = s.get(JobRow, job_id)
        assert row is not None
        return row


def _only_job() -> JobRow:
    with Session(get_engine()) as s:
        from sqlmodel import select

        rows = s.exec(select(JobRow)).all()
    assert len(rows) == 1
    return rows[0]


def _captures(data_dir: Path) -> list[str]:
    return sorted(p.name for p in (data_dir / "videos" / "h4wkDemo001" / "captures").iterdir())


def _post(client: TestClient) -> None:
    r = client.post("/api/collect", json={"url": VIDEO, "level": "text"})
    assert r.status_code == 202, r.text


def test_stopped_between_collect_and_media(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fetched: list[Cap] = []
    original = SampleCollector.fetch

    def counting(self, cap, target, workdir):  # noqa: ANN001, ANN202
        fetched.append(cap)
        return original(self, cap, target, workdir)

    monkeypatch.setattr(SampleCollector, "fetch", counting)
    with monkeypatch.context() as m:
        m.setattr(pipeline, "media", lambda job_id: None)
        _post(client)
    job = _only_job()
    assert (job.status, job.step) == ("running", "collect") and job.capture
    calls, captures = len(fetched), _captures(data_dir)

    assert recovery.recover("default") == []
    assert recovery.recover("gpu") == [job.id]
    done = _job(job.id)
    assert done.status == "done", done.error
    assert len(fetched) == calls and _captures(data_dir) == captures


def test_stopped_inside_media(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise KeyboardInterrupt

    with monkeypatch.context() as m:
        m.setattr(ocr, "process_ocr", boom)
        _post(client)  # Huey bắt KeyboardInterrupt, job dừng ở bước ocr
    job = _only_job()
    assert (job.status, job.step) == ("running", "ocr")
    captures = _captures(data_dir)
    assert recovery.recover("default") == []
    assert recovery.recover("gpu") == [job.id]
    assert _job(job.id).status == "done"
    assert _captures(data_dir) == captures and len(captures) == 1


def test_stopped_after_media_resumes_at_analyze(client: TestClient) -> None:
    _post(client)
    job = _only_job()
    with Session(get_engine()) as s:
        row = s.get(JobRow, job.id)
        assert row is not None
        row.status, row.step, row.progress = "running", "vlm", 70
        s.add(row)
        s.commit()
        assert recovery.next_task(row) == "analyze"
    assert recovery.recover("gpu") == []
    assert recovery.recover("default") == [job.id]
    assert _job(job.id).status == "done"


def test_recover_does_not_enqueue_twice_and_audits(
    client: TestClient, data_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pipeline, "collect", lambda job_id: None)
    job = pipeline.create_job(VIDEO, "h4wkDemo001", "text", False, "user:thi")
    pipeline._update(job.id, status="running", step="collect")
    assert recovery.recover("default") == [job.id]
    assert recovery.recover("default") == []
    lines = (data_dir / "log" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    rec = [json.loads(x) for x in lines if '"job.recover"' in x]
    assert len(rec) == 1 and rec[0]["target"] == job.id
    assert rec[0]["actor"] == "system:recovery"
