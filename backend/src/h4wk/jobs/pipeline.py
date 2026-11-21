"""Luồng collect → media → analyze (T12). Mỗi bước là một task Huey; media chạy trên hàng
đợi gpu. Mỗi bước cập nhật trạng thái và tiến độ của job trong chỉ mục."""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import cv2
from pydantic import TypeAdapter
from sqlmodel import Session, select

from h4wk.ai.gateway import AIGateway
from h4wk.analysis import faces, refimages, runner, verdict
from h4wk.analysis.models import EntityHit, Finding
from h4wk.collectors.models import CollectLevel, Normalized
from h4wk.collectors.orchestrator import Orchestrator
from h4wk.collectors.targets import Target, TargetKind, parse_target
from h4wk.core import audit, events
from h4wk.core.config import config_dir, data_dir
from h4wk.core.config_models import AnalysisConfig, SourcesConfig, load_toml
from h4wk.core.db import FindingRow, JobRow, finding_row, get_engine
from h4wk.core.entities import REF_FILE, load_entities, refs_dir
from h4wk.core.ids import new_ulid
from h4wk.core.types import VN_TZ
from h4wk.evidence.models import Manifest, Trigger
from h4wk.evidence.writer import CAPTURE_TS_FORMAT, list_captures
from h4wk.jobs.queue import huey, huey_gpu
from h4wk.media import ocr, stt, transcripts
from h4wk.media.enrich import enrich
from h4wk.media.keyframes import Keyframe, extract_keyframes, select_keyframes, write_selected
from h4wk.media.timeline import Timeline

_stt_worker = stt.SttWorker(os.getenv("H4WK_STT_MODEL", "large-v3"))
_ref_embedder = refimages.DinoEmbedder()
logger = logging.getLogger(__name__)

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


def _event(job: JobRow, kind: events.EventKind, message: str) -> None:
    watch = job.trigger.removeprefix(_WATCH) if job.trigger.startswith(_WATCH) else None
    events.record(kind, message, video_id=job.video_id, job_id=job.id, watch_item=watch)


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


def playlist_video_ids(playlist_id: str) -> list[str]:
    """ID video của playlist, cắt theo collect.playlist_max_videos trong sources.toml."""
    path = config_dir() / "sources.toml"
    cfg = load_toml(path, SourcesConfig) if path.exists() else SourcesConfig()
    ids = Orchestrator.from_config(root=data_dir()).list_video_ids(
        Target(TargetKind.PLAYLIST, playlist_id)
    )
    return ids[: cfg.collect.playlist_max_videos]


def _analysis_config() -> AnalysisConfig:
    path = config_dir() / "analysis.toml"
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
    # "queued" kèm bước kế tiếp trong lúc chờ hàng đợi: running chỉ còn nghĩa là đang chạy thật.
    _update(job_id, status="queued", step="media", capture=capture, progress=40)
    media(job_id)


def _select_frames(
    job: JobRow, out: Path, candidates: list[Keyframe], lines: list[ocr.OcrLine]
) -> list[Keyframe]:
    """Chọn keyframe theo embedding ảnh (DINOv2) và chữ OCR; ghi frames/selected.json."""
    texts: dict[str, list[tuple[str, float]]] = {}
    for line in lines:
        texts.setdefault(line.frame, []).append((line.text, line.score))
    try:
        images = [
            cv2.cvtColor(cv2.imread(str(out / f.file)), cv2.COLOR_BGR2RGB) for f in candidates
        ]
        vectors = _ref_embedder.embed(images)
    except Exception as e:
        # Thiếu torch, hết VRAM...: chỉ bỏ được khung trùng chữ và trùng hash.
        logger.warning("Frame embedding failed, keeping near-duplicate frames: %s", e)
        audit.log(job.trigger, "media.frames", job.id, {"error": str(e)}, status="error")
        vectors = None
    frames = select_keyframes(candidates, texts, vectors)
    write_selected(out, frames)
    return frames


def _match(
    job: JobRow,
    cap_dir: Path,
    out: Path,
    frames: list[Keyframe],
    thumbnails: list[str],
    timeline: Timeline,
) -> None:
    """Khớp keyframe và thumbnail cục bộ với ảnh mẫu; ghi ref_hits.json."""
    # Xoá kết quả cũ để lần chạy lại (thu lại cùng bản thu, recovery) không dùng dấu hiệu lỗi thời.
    (out / "ref_hits.json").unlink(missing_ok=True)
    if not _analysis_config().ref_image.enabled:
        return
    refs = {}
    for entity in load_entities():
        folder = refs_dir(entity.id, "image")
        files = (
            sorted(p for p in folder.glob("*") if REF_FILE.match(p.name)) if folder.is_dir() else []
        )
        if files:
            refs[entity.id] = files
    if not refs:
        return
    images = [(f.file, out / f.file) for f in frames] + [
        (t, cap_dir / t) for t in thumbnails if (cap_dir / t).is_file()
    ]
    try:
        matches = refimages.match_refs(
            images,
            refs,
            _ref_embedder,
            _analysis_config().ref_image.threshold,
            out / "embeddings.npz",
        )
    except ImportError:
        logger.warning("Skipping reference image matching: torch is not installed")
        audit.log(job.trigger, "media.match", job.id, {"skipped": "torch not installed"})
        return
    except Exception as e:
        # Tải model lỗi (mất mạng), hết VRAM...: bỏ qua bước này, job vẫn chạy tiếp tới analyze.
        logger.warning("Reference image matching failed: %s", e)
        audit.log(job.trigger, "media.match", job.id, {"error": str(e)}, status="error")
        return
    hits = refimages.to_hits(matches, timeline, {f.file: f.t for f in frames})
    content = [h.model_dump(mode="json", by_alias=True) for h in hits]
    (out / "ref_hits.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _faces(job, cap_dir, out, frames, thumbnails, timeline):
    target = out / "face_hits.json"
    target.unlink(missing_ok=True)
    if not _analysis_config().face.enabled:
        return
    try:
        refs = {
            entity.id: sorted(
                p for p in refs_dir(entity.id, "face").glob("*") if REF_FILE.match(p.name)
            )
            for entity in load_entities()
        }
        refs = {entity: paths for entity, paths in refs.items() if paths}
        if not refs:
            return
        images = [(f.file, out / f.file) for f in frames] + [
            (t, cap_dir / t) for t in thumbnails if (cap_dir / t).is_file()
        ]
        matches = faces.match_faces(images, refs)
        hits = faces.to_hits(matches, timeline, {f.file: f.t for f in frames})
        target.write_text(
            json.dumps([h.model_dump(mode="json", by_alias=True) for h in hits], ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("Face matching failed: %s", e)
        audit.log(job.trigger, "media.face", job.id, {"error": str(e)}, status="error")


@huey_gpu.task()
def media(job_id: str) -> None:
    job = _update(job_id, status="running", step="media", progress=45)
    try:
        cap_dir = _video_dir(job) / "captures" / str(job.capture)
        out = _video_dir(job) / "derived" / str(job.capture)
        out.mkdir(parents=True, exist_ok=True)
        data = Normalized.model_validate_json((cap_dir / "normalized.json").read_bytes())
        frames = []
        source_hash = None
        has_video = any(m.kind == "video" for m in data.media)
        # Bản thu full không có video (vd yt-dlp bị tắt): bỏ STT và keyframe, vẫn phân tích văn bản.
        if job.level == CollectLevel.FULL and has_video:
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
            thumbnails = list(dict.fromkeys(t.file for t in data.thumbnails if t.file))
            if frames:
                # OCR chạy trên mọi khung ứng viên; timeline và khớp ảnh chỉ dùng keyframe.
                frames = _select_frames(job, out, frames, lines)
                kept = {f.file for f in frames} | set(thumbnails)
                lines = [line for line in lines if line.frame in kept]
            enrich(timeline, out, frames, thumbnails, lines)
            job = _update(job_id, step="match", progress=68)
            _match(job, cap_dir, out, frames, thumbnails, timeline)
            _faces(job, cap_dir, out, frames, thumbnails, timeline)
    except Exception as e:
        _fail(job_id, job.step or "media", e)
        return
    _update(job_id, status="queued", step="analyze", progress=70)
    analyze(job_id)


class AnalysisQuotaError(RuntimeError):
    """Không công bố run CLI khi hết quota."""


def analyze_capture(video_dir: Path, cap: str, gateway: AIGateway, *, reject_quota: bool = False):
    """Phân tích bản thu đã có timeline, không thu lại hay chạy media."""
    derived = video_dir / "derived" / cap
    timeline = Timeline.model_validate_json((derived / "timeline.json").read_text("utf-8"))
    n = Normalized.model_validate_json(
        (video_dir / "captures" / cap / "normalized.json").read_text("utf-8")
    )
    run_id = f"r_{new_ulid()}"
    ref_hits = []
    for name in ("ref_hits.json", "face_hits.json"):
        path = derived / name
        if path.is_file():
            ref_hits.extend(TypeAdapter(list[EntityHit]).validate_json(path.read_bytes()))
    # T11: dấu hiệu tên và tầng tĩnh; runner ghi hits.json và findings.json.
    settings = _analysis_config()
    out = derived / "analysis" / run_id

    def check_quota(error: str | None) -> None:
        if (
            reject_quota
            and error
            and any(word in error.lower() for word in ("quota", "429", "resource_exhausted"))
        ):
            raise AnalysisQuotaError(error)

    def run(target: Path):
        _hits, findings, llm_error = runner.analyze(
            n,
            timeline,
            load_entities(),
            None,
            run_id,
            target,
            comment_settings=settings.comments,
            jev_settings=settings.jev,
            extra_hits=ref_hits,
        )
        check_quota(llm_error)
        decision, verdict_error = verdict.decide(n, findings, run_id, timeline, gateway)
        verdict.write(target / "verdict.json", decision)
        llm_error = "; ".join(e for e in (llm_error, verdict_error) if e) or None
        return findings, llm_error

    if reject_quota:
        with TemporaryDirectory(prefix=".reanalyze-", dir=derived) as staging:
            target = Path(staging) / run_id
            findings, llm_error = run(target)
            check_quota(llm_error)
            out.parent.mkdir(parents=True, exist_ok=True)
            target.rename(out)
    else:
        findings, llm_error = run(out)
    with Session(get_engine()) as s:
        for f in findings:
            s.add(finding_row(f))
        s.commit()
    return run_id, findings, llm_error


@huey.task()
def analyze(job_id: str) -> None:
    job = _update(job_id, status="running", step="analyze", progress=75)
    try:
        cap = str(job.capture)
        run_id, findings, llm_error = analyze_capture(_video_dir(job), cap, AIGateway())
    except Exception as e:
        _fail(job_id, "analyze", e)
        return
    job = _update(job_id, status="done", step=None, progress=100, run_id=run_id)
    message = f"Processed video {job.video_id}: {len(findings)} findings"
    detail = {"capture": cap, "run_id": run_id, "findings": len(findings)}
    notes = []
    if llm_error:
        short = llm_error[:200] + ("…" if len(llm_error) > 200 else "")
        notes.append(f"LLM analysis skipped: {short}")
        detail["llm_error"] = llm_error
    if notes:
        message += f" ({'; '.join(notes)})"
    _event(job, "job_done", message)
    audit.log(job.trigger, "job.run", job.id, detail)


def _latest_runs(root: Path) -> dict[tuple[str, str], str]:
    """run_id mới nhất của mỗi (video, bản thu), chỉ tính run có findings.json."""
    latest: dict[tuple[str, str], str] = {}
    for path in root.glob("videos/*/derived/*/analysis/*/findings.json"):
        run = path.parent
        key = (run.parents[3].name, run.parents[1].name)
        latest[key] = max(latest.get(key, ""), run.name)
    return latest


def latest_findings(latest_only: bool = False) -> list[Finding]:
    """Nghi vấn của lần chạy mới nhất cho mỗi bản thu. latest_only=True: chỉ giữ bản thu
    mới nhất đã phân tích của mỗi video, để thu lại cùng video không làm lặp nghi vấn.
    "Mới nhất" xác định từ findings.json trong data/ (nguồn gốc), không từ bảng jobs, nên kết
    quả trước và sau reindex giống nhau. Run mới nhất không có nghi vấn thì bản thu đó
    không hiện nghi vấn nào, run cũ không hiện lại.
    Hạn chế: findings.json được ghi trước khi commit FindingRow. Commit DB lỗi thì bản thu
    hiện 0 nghi vấn cho tới khi chạy `h4wk reindex`. findings.json hỏng thì run đó vẫn được
    coi là mới nhất (chỉ xét tên file), phải sửa hoặc xoá file."""
    latest = _latest_runs(data_dir())
    newest: dict[str, str] = {}
    for vid, cap in latest:
        newest[vid] = max(newest.get(vid, ""), cap)
    with Session(get_engine()) as s:
        rows = s.exec(select(FindingRow)).all()
    return [
        Finding.model_validate_json(r.data)
        for r in rows
        if latest.get((r.video_id, r.capture)) == r.run_id
        and (not latest_only or newest[r.video_id] == r.capture)
    ]
