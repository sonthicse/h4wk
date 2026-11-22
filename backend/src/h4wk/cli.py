"""CLI `h4wk`."""

import shutil
from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter

from h4wk.analysis import verdict
from h4wk.analysis.models import (
    Finding,
)
from h4wk.core.config import config_dir, data_dir
from h4wk.core.db import get_engine
from h4wk.evidence.verify import FileStatus
from h4wk.evidence.verify import verify as verify_capture
from h4wk.media.timeline import Timeline

app = typer.Typer(no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Công cụ dòng lệnh của h4wk."""


def init_workspace(data_dir: Path, config_dir: Path) -> list[Path]:
    """Tạo thư mục dữ liệu và chép config/*.toml.example thành *.toml nếu chưa có.

    Không ghi đè file *.toml đã có vì đó là cấu hình thật của từng máy.
    Trả về danh sách file cấu hình vừa tạo.
    """
    data_dir.mkdir(parents=True, exist_ok=True)
    get_engine(data_dir)  # tạo database chỉ mục nếu chưa có
    # Chuyển đối tượng và watchlist từ chỗ lưu cũ (data/, database) sang config/ trước khi chép
    # file mẫu, để file mẫu rỗng không đè mất dữ liệu cũ.
    from h4wk.core.entities import migrate_legacy as migrate_entities
    from h4wk.watchlist.service import migrate_legacy as migrate_watchlist

    migrate_entities()
    migrate_watchlist()
    created: list[Path] = []
    for example in sorted(config_dir.glob("*.toml.example")):
        target = example.with_suffix("")  # bỏ đuôi .example
        if not target.exists():
            shutil.copyfile(example, target)
            created.append(target)
    return created


@app.command()
def init() -> None:
    """Tạo data/ và config/*.toml từ file mẫu. Không tự thêm đối tượng hay kênh nào."""
    d = data_dir()
    created = init_workspace(data_dir=d, config_dir=config_dir())
    typer.echo(f"data dir: {d}")
    for path in created:
        typer.echo(f"created: {path}")


@app.command("analyze")
def reanalyze(
    video_id: Annotated[str | None, typer.Argument()] = None,
    all_videos: Annotated[bool, typer.Option("--all")] = False,
) -> None:
    """Phân tích lại bản thu mới nhất mà không thu lại hoặc chạy media."""
    from h4wk.jobs.pipeline import AnalysisQuotaError, analyze_capture

    if (video_id is None) == (not all_videos):
        raise typer.BadParameter("Specify a video ID or --all, not both")
    if video_id is not None and (Path(video_id).name != video_id or video_id in {".", ".."}):
        raise typer.BadParameter("Invalid video ID")
    root = data_dir() / "videos"
    videos = sorted(p for p in root.glob("*") if p.is_dir()) if all_videos else [root / video_id]
    pending = []
    for video in videos:
        capture = max((video / "captures").glob("*/normalized.json"), default=None)
        if (
            capture is None
            or not (video / "derived" / capture.parent.name / "timeline.json").is_file()
        ):
            if not all_videos:
                raise typer.BadParameter(f"No prepared capture for {video.name}")
            continue
        pending.append((video, capture.parent.name))
    for video, cap in pending:
        try:
            run_id, findings, error = analyze_capture(video, cap, reject_quota=True)
        except AnalysisQuotaError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        typer.echo(f"{video.name}: {run_id} ({len(findings)} findings)")
        if error:
            typer.echo(error, err=True)


@app.command("verdict")
def backfill_verdict(
    video_id: Annotated[str | None, typer.Argument()] = None,
    all_videos: Annotated[bool, typer.Option("--all")] = False,
    force: Annotated[bool, typer.Option("--force")] = False,
) -> None:
    """Tạo kết luận cho lần phân tích mới nhất."""
    root = data_dir() / "videos"
    if (video_id is None) == (not all_videos):
        raise typer.BadParameter("Specify a video ID or --all, not both")
    if video_id is not None and (Path(video_id).name != video_id or video_id in {".", ".."}):
        raise typer.BadParameter("Invalid video ID")
    videos = sorted(p for p in root.glob("*") if p.is_dir()) if all_videos else [root / video_id]
    pending = []
    for video in videos:
        capture = max((video / "captures").glob("*/normalized.json"), default=None)
        derived = video / "derived" / capture.parent.name if capture else None
        latest = max(derived.glob("analysis/*/findings.json"), default=None) if derived else None
        if latest is None:
            if not all_videos:
                raise typer.BadParameter(f"No analysis for {video.name}")
            continue
        target = latest.with_name("verdict.json")
        if target.exists() and not force:
            if not all_videos:
                typer.echo(f"Already exists: {target}")
            continue
        pending.append((derived, latest, target))
    for derived, latest, target in pending:
        timeline = Timeline.model_validate_json(
            (derived / "timeline.json").read_text(encoding="utf-8")
        )
        findings = TypeAdapter(list[Finding]).validate_json(latest.read_text(encoding="utf-8"))
        verdict.write(target, verdict.decide(findings, latest.parent.name, timeline))
        typer.echo(f"wrote: {target}")


@app.command()
def verify(capture_dir: Path) -> None:
    """Kiểm tra toàn vẹn một bản thu: tính lại SHA-256 từng file và so với manifest."""
    results = verify_capture(capture_dir)
    for r in results:
        typer.echo(f"{r.status.value:<10} {r.path}")
    if any(r.status != FileStatus.OK for r in results):
        raise typer.Exit(code=1)


@app.command()
def reindex(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt."),
) -> None:
    """Xoá index.db rồi dựng lại đối tượng, nghi vấn, quyết định rà soát từ file trong data/."""
    if not yes:
        typer.confirm(
            "This deletes index.db: sessions, watchlist, known videos and job "
            "history will be lost. Stop the API and workers first. Continue?",
            abort=True,
        )
    from h4wk.core.reindex import reindex as run

    result = run()
    typer.echo(f"entities: {result.entities}")
    typer.echo(f"videos: {result.videos}")
    typer.echo(f"findings: {result.findings}")
    typer.echo(f"decisions: {result.decisions}")
    for item in result.skipped:
        typer.echo(f"skipped: {item}")


def main() -> None:
    app()
