"""Luồng collect → media → analyze (T12). Mỗi bước là một task Huey; media chạy trên hàng
đợi gpu. Mỗi bước cập nhật trạng thái và tiến độ của job trong chỉ mục."""

import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from h4wk.analysis import runner
from h4wk.analysis.models import Finding
from h4wk.collectors.models import CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.targets import parse_target
from h4wk.core import audit
from h4wk.core.config import CONFIG_DIR, data_dir
from h4wk.core.config_models import AnalysisConfig, load_toml
from h4wk.core.db import EventRow, FindingRow, JobRow, get_engine
from h4wk.core.entities import load_entities
from h4wk.core.ids import new_ulid
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Manifest, Trigger
from h4wk.evidence.writer import CAPTURE_TS_FORMAT, list_captures
from h4wk.jobs.queue import huey, huey_gpu
from h4wk.media import ocr, stt, transcripts
from h4wk.media.enrich import enrich
from h4wk.media.keyframes import extract_keyframes
from h4wk.media.timeline import Timeline

_stt_worker = stt.SttWorker(os.getenv("H4WK_STT_MODEL", "large-v3"))

RECENT = timedelta(minutes=10)


def _now() -> datetime:
    return datetime.now(VN_TZ)


def create_job(target: str, video_id: str, level: str, force: bool, trigger: str) -> JobRow:
    now = _now()
    job = JobRow(
        id=f"j_{new_ulid()}",
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
    return data_dir() / "videos" / job.video_id


def _event(job: JobRow, kind: str, message: str) -> None:
    with Session(get_engine()) as s:
        s.add(
            EventRow(
                at=_now(),
                kind=kind,
                message=message,
                video_id=job.video_id,
                job_id=job.id,
                watch_item=job.trigger.removeprefix(_WATCH)
                if job.trigger.startswith(_WATCH)
                else None,
            )
        )
        s.commit()


_WATCH = "system:watchlist:"


def _trigger(job: JobRow) -> Trigger:
    if job.trigger.startswith(_WATCH):
        return Trigger(
            type="watchlist", watch_item=job.trigger.removeprefix(_WATCH), event="new_video"
        )
    return Trigger(type="manual")


def _fail(job_id: str, step: str, e: Exception) -> None:
    job = _update(job_id, status="failed", error=f"{step}: {e}")
    _event(job, "job_failed", f"Job failed for video {job.video_id} at {step}")
    audit.log(job.trigger, "job.run", job.id, {"step": step, "error": str(e)}, status="error")


def _recent_capture(job: JobRow) -> str | None:
    caps = list_captures(_video_dir(job) / "captures")
    if not caps:
        return None
    at = datetime.strptime(caps[-1], CAPTURE_TS_FORMAT).replace(tzinfo=VN_TZ)
    if _now() - at >= RECENT:
        return None
    manifest = Manifest.model_validate_json(
        (_video_dir(job) / "captures" / caps[-1] / "manifest.json").read_bytes()
    )
    return caps[-1] if manifest.level == job.level else None


def _analysis_config() -> AnalysisConfig:
    path = CONFIG_DIR / "analysis.toml"
    return load_toml(path, AnalysisConfig) if path.exists() else AnalysisConfig()


def start(job_id: str) -> None:
    collect(job_id)


@huey.task()
def collect(job_id: str) -> None:
    job = _update(job_id, status="running", step="collect", progress=5)
    try:
        capture = None if job.force else _recent_capture(job)
        if capture is None:
            # C1 dùng tên bản thu chính xác đến giây.
            now = _now()
            if (_video_dir(job) / "captures" / now.strftime(CAPTURE_TS_FORMAT)).exists():
                time.sleep(1 - now.microsecond / 1_000_000)
            orch = Orchestrator.from_config(root=data_dir())
            path = orch.collect(
                parse_target(job.target),
                CollectLevel(job.level),
                collector=job.trigger,
                trigger=_trigger(job),
            )
            capture = path.name
            n = Normalized.model_validate_json((path / "normalized.json").read_text("utf-8"))
            if n.video is None:
                # Bản thu vẫn được giữ làm bằng chứng của lần thu thất bại.
                raise RuntimeError(f"no source returned video metadata (capture {capture})")
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
        out = _video_dir(job) / "derived" / str(job.capture)
        out.mkdir(parents=True, exist_ok=True)
        data = Normalized.model_validate_json((cap_dir / "normalized.json").read_bytes())
        frames = []
        source_hash = None
        if job.level == CollectLevel.FULL:
            job = _update(job_id, step="transcribe", progress=48)
            video_file = stt.transcribe_capture(cap_dir, out, _stt_worker)
            manifest = Manifest.model_validate_json((cap_dir / "manifest.json").read_bytes())
            source_hash = manifest.files[video_file].sha256
            job = _update(job_id, step="frames", progress=55)
            frames = extract_keyframes(out)
        timeline = transcripts.read_capture_timeline(cap_dir, out, _analysis_config())
        timeline.source_video_sha256 = source_hash
        if job.level == CollectLevel.METADATA:
            transcripts.write_timeline(out / "timeline.json", timeline)
        else:
            job = _update(job_id, step="ocr", progress=60)
            lines = ocr.process_ocr(cap_dir, out)
            job = _update(job_id, step="vlm", progress=65)
            thumbnails = list(dict.fromkeys(t.file for t in data.thumbnails if t.file))
            enrich(timeline, cap_dir, out, frames, thumbnails, lines)
    except Exception as e:
        _fail(job_id, job.step or "media", e)
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
        # T11: dấu hiệu tên và tầng tĩnh; runner ghi hits.json và findings.json.
        _hits, findings = runner.analyze(
            n, timeline, load_entities(), None, run_id, derived / "analysis" / run_id
        )
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
    except Exception as e:
        _fail(job_id, "analyze", e)
        return
    job = _update(job_id, status="done", step=None, progress=100, run_id=run_id)
    _event(job, "job_done", f"Processed video {job.video_id}: {len(findings)} findings")
    audit.log(
        job.trigger,
        "job.run",
        job.id,
        {"capture": cap, "run_id": run_id, "findings": len(findings)},
    )


def latest_findings() -> list[Finding]:
    """Nghi vấn của lần chạy mới nhất cho mỗi bản thu."""
    with Session(get_engine()) as s:
        rows = s.exec(select(FindingRow)).all()
    latest: dict[tuple[str, str], str] = {}
    for r in rows:
        key = (r.video_id, r.capture)
        latest[key] = max(latest.get(key, ""), r.run_id)
    return [
        Finding.model_validate_json(r.data)
        for r in rows
        if latest[(r.video_id, r.capture)] == r.run_id
    ]
