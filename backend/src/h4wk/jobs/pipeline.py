"""Luồng collect → media → analyze (T12). Mỗi bước là một task Huey; media chạy trên hàng
đợi gpu. Mỗi bước cập nhật trạng thái và tiến độ của job trong chỉ mục."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from h4wk.analysis.models import Finding
from h4wk.collectors.models import CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.targets import parse_target
from h4wk.core import audit
from h4wk.core.cases import case_dir, load_case
from h4wk.core.db import FindingRow, JobRow, get_engine
from h4wk.core.ids import new_ulid
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Manifest, Trigger
from h4wk.evidence.writer import CAPTURE_TS_FORMAT, list_captures
from h4wk.jobs import placeholder
from h4wk.jobs.queue import huey, huey_gpu
from h4wk.media.timeline import Timeline

RECENT = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(VN_TZ)


def create_job(
    case_id: str, target: str, video_id: str, level: str, force: bool, trigger: str
) -> JobRow:
    now = _now()
    job = JobRow(
        id=f"j_{new_ulid()}",
        case_id=case_id,
        target=target,
        video_id=video_id,
        level=level,
        force=force,
        trigger=trigger,
        created_at=now,
        updated_at=now,
    )
    with Session(get_engine()) as s:
        s.add(job)
        s.commit()
        s.refresh(job)
    return job


def _update(job_id: str, **fields: object) -> JobRow:
    with Session(get_engine()) as s:
        job = s.get(JobRow, job_id)
        assert job is not None
        for k, v in fields.items():
            setattr(job, k, v)
        job.updated_at = _now()
        s.add(job)
        s.commit()
        s.refresh(job)
        return job


def _video_dir(job: JobRow) -> Path:
    return case_dir(job.case_id) / "videos" / job.video_id


def _fail(job_id: str, step: str, e: Exception) -> None:
    job = _update(job_id, status="failed", error=f"{step}: {e}")
    audit.log(
        job.case_id, job.trigger, "job.run", job.id, {"step": step, "error": str(e)}, status="error"
    )


def _recent_capture(job: JobRow) -> str | None:
    caps = list_captures(_video_dir(job) / "captures")
    if not caps:
        return None
    at = datetime.strptime(caps[-1], CAPTURE_TS_FORMAT).replace(tzinfo=VN_TZ)
    return caps[-1] if _now() - at < RECENT else None


def start(job_id: str) -> None:
    collect(job_id)


@huey.task()
def collect(job_id: str) -> None:
    job = _update(job_id, status="running", step="collect", progress=5)
    try:
        capture = None if job.force else _recent_capture(job)
        if capture is None:
            orch = Orchestrator.from_config(case_dir=case_dir(job.case_id))
            path = orch.collect(
                parse_target(job.target),
                CollectLevel(job.level),
                collector=job.trigger,
                trigger=Trigger(type="manual"),
            )
            capture = path.name
            n = Normalized.model_validate_json((path / "normalized.json").read_text("utf-8"))
            if n.video is None:
                # Bản thu vẫn được giữ làm bằng chứng của lần thu thất bại.
                raise RuntimeError(f"không nguồn nào lấy được metadata video (bản thu {capture})")
    except Exception as e:
        _fail(job_id, "collect", e)
        return
    _update(job_id, capture=capture, progress=40)
    media(job_id)


@huey_gpu.task()
def media(job_id: str) -> None:
    job = _update(job_id, step="media", progress=45)
    try:
        cap_dir = _video_dir(job) / "captures" / str(job.capture)
        n = Normalized.model_validate_json((cap_dir / "normalized.json").read_text("utf-8"))
        m = Manifest.model_validate_json((cap_dir / "manifest.json").read_text("utf-8"))
        video_sha = next((m.files[f.file].sha256 for f in n.media if f.file in m.files), None)
        timeline = placeholder.build_timeline(n, job.video_id, str(job.capture), video_sha)
        out = _video_dir(job) / "derived" / str(job.capture)
        out.mkdir(parents=True, exist_ok=True)
        (out / "timeline.json").write_text(timeline.model_dump_json(indent=2), "utf-8")
    except Exception as e:
        _fail(job_id, "media", e)
        return
    _update(job_id, progress=70)
    analyze(job_id)


@huey.task()
def analyze(job_id: str) -> None:
    job = _update(job_id, step="analyze", progress=75)
    try:
        cap = str(job.capture)
        derived = _video_dir(job) / "derived" / cap
        timeline = Timeline.model_validate_json((derived / "timeline.json").read_text("utf-8"))
        n = Normalized.model_validate_json(
            (_video_dir(job) / "captures" / cap / "normalized.json").read_text("utf-8")
        )
        run_id = f"r_{new_ulid()}"
        hits, findings = placeholder.analyze(load_case(job.case_id), n, timeline, run_id)
        run_dir = derived / "analysis" / run_id
        run_dir.mkdir(parents=True)
        for name, items in [("hits.json", hits), ("findings.json", findings)]:
            data = [x.model_dump(mode="json") for x in items]
            (run_dir / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
        with Session(get_engine()) as s:
            for f in findings:
                s.add(
                    FindingRow(
                        id=f.id,
                        case_id=f.case_id,
                        video_id=f.video_id,
                        capture=f.capture,
                        run_id=f.run_id,
                        data=f.model_dump_json(),
                    )
                )
            s.commit()
    except Exception as e:
        _fail(job_id, "analyze", e)
        return
    job = _update(job_id, status="done", step=None, progress=100, run_id=run_id)
    audit.log(
        job.case_id,
        job.trigger,
        "job.run",
        job.id,
        {"capture": cap, "run_id": run_id, "findings": len(findings)},
    )


def latest_findings(case_id: str) -> list[Finding]:
    """Nghi vấn của lần chạy mới nhất cho mỗi bản thu."""
    with Session(get_engine()) as s:
        rows = s.exec(select(FindingRow).where(FindingRow.case_id == case_id)).all()
    latest: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r.video_id, r.capture)
        latest[key] = max(latest.get(key, ""), r.run_id)
    return [
        Finding.model_validate_json(r.data)
        for r in rows
        if latest[(r.video_id, r.capture)] == r.run_id
    ]
