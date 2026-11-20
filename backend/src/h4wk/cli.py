"""CLI `h4wk`."""

import csv
import json
import shutil
from pathlib import Path
from typing import Annotated

import typer
from pydantic import TypeAdapter

from h4wk.analysis.evaluation import collect_units, markdown_table, sample, score
from h4wk.analysis.models import EntityHit, Finding, ReviewDecision
from h4wk.collectors.models import Normalized
from h4wk.core.auth import create_user
from h4wk.core.config import CONFIG_DIR, REPO_ROOT, data_dir
from h4wk.core.config_models import AiConfig, AnalysisConfig, SourcesConfig
from h4wk.core.db import get_engine
from h4wk.evidence.models import Manifest
from h4wk.evidence.verify import FileStatus
from h4wk.evidence.verify import verify as verify_capture
from h4wk.media.timeline import Timeline

app = typer.Typer(no_args_is_help=True)
schema_app = typer.Typer(no_args_is_help=True, help="JSON Schema của hợp đồng C1–C5.")
app.add_typer(schema_app, name="schema")
user_app = typer.Typer(no_args_is_help=True, help="Tài khoản đăng nhập.")
app.add_typer(user_app, name="user")
eval_app = typer.Typer(no_args_is_help=True, help="So sánh tầng tĩnh và LLM (T38).")
app.add_typer(eval_app, name="eval")

# Tên file → kiểu cần xuất JSON Schema.
CONTRACTS: dict[str, object] = {
    "c1-manifest": Manifest,
    "c2-normalized": Normalized,
    "c3-timeline": Timeline,
    "c4-hits": list[EntityHit],
    "c4-findings": list[Finding],
    "c4-review-decision": ReviewDecision,
    "c5-sources": SourcesConfig,
    "c5-ai": AiConfig,
    "c5-analysis": AnalysisConfig,
}


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
    created: list[Path] = []
    for example in sorted(config_dir.glob("*.toml.example")):
        target = example.with_suffix("")  # bỏ đuôi .example
        if not target.exists():
            shutil.copyfile(example, target)
            created.append(target)
    return created


@app.command()
def init() -> None:
    """Tạo data/ và config/*.toml từ file mẫu."""
    d = data_dir()
    created = init_workspace(data_dir=d, config_dir=CONFIG_DIR)
    typer.echo(f"data dir: {d}")
    for path in created:
        typer.echo(f"created: {path}")
    from h4wk.watchlist.service import seed_defaults

    for item in seed_defaults():
        typer.echo(f"watchlist: {item.id} {item.handle} ({item.level})")


def export_schemas(out_dir: Path) -> list[Path]:
    """Ghi JSON Schema của C1–C5 vào out_dir. Nội dung ổn định giữa các lần chạy."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, tp in CONTRACTS.items():
        schema = TypeAdapter(tp).json_schema(mode="validation")
        path = out_dir / f"{name}.json"
        text = json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written


@schema_app.command("export")
def schema_export() -> None:
    """Xuất JSON Schema của C1–C5 vào docs/contracts/."""
    for path in export_schemas(REPO_ROOT / "docs" / "contracts"):
        typer.echo(f"wrote: {path}")


@user_app.command("create")
def user_create(
    username: str,
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Tạo tài khoản; mật khẩu được hỏi khi chạy và lưu dạng hash argon2."""
    try:
        create_user(username, password)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"created user: {username}")


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
            "This deletes index.db: accounts, sessions, watchlist, known videos and job "
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
    typer.echo("Recreate accounts with: h4wk user create <username>")


EVAL_DIR = REPO_ROOT / "docs" / "eval"
LABEL_COLUMNS = [
    "unit_id",
    "video_id",
    "capture",
    "place",
    "kind",
    "entity",
    "text",
    "label",
    "note",
]
PREDICTION_COLUMNS = ["unit_id", "run_id", "static", "llm"]


def _write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@eval_app.command("sample")
def eval_sample(
    n: int = typer.Option(50, help="Number of units to sample."),
    seed: int = typer.Option(0, help="Random seed."),
    out: Annotated[Path, typer.Option(help="Output directory.")] = EVAL_DIR,
    force: bool = typer.Option(False, "--force", help="Overwrite existing files."),
) -> None:
    """Lấy mẫu các mục cần gán nhãn từ data/ và ghi labels.csv, predictions.csv."""
    labels, predictions = out / "labels.csv", out / "predictions.csv"
    if not force and (labels.exists() or predictions.exists()):
        typer.echo(f"Error: {labels} or {predictions} already exists; use --force.", err=True)
        raise typer.Exit(code=1)
    units = collect_units(data_dir())
    chosen = sample(units, n, seed)
    out.mkdir(parents=True, exist_ok=True)
    _write_csv(
        labels,
        LABEL_COLUMNS,
        [
            {**{c: getattr(u, c) for c in LABEL_COLUMNS[:7]}, "label": "", "note": ""}
            for u in chosen
        ],
    )
    _write_csv(
        predictions,
        PREDICTION_COLUMNS,
        [
            {
                "unit_id": u.unit_id,
                "run_id": u.run_id,
                "static": int(u.static),
                "llm": int(u.llm),
            }
            for u in chosen
        ],
    )
    typer.echo(f"found: {len(units)} units")
    typer.echo(f"sampled: {len(chosen)} units -> {out}")


@eval_app.command("score")
def eval_score(
    dir: Annotated[Path, typer.Option(help="Directory of the CSV files.")] = EVAL_DIR,
) -> None:
    """Chấm precision/recall của tầng tĩnh và tầng LLM theo nhãn đã gán."""
    predictions = {r["unit_id"]: r for r in _read_csv(dir / "predictions.csv")}
    rows = [
        {**r, **predictions[r["unit_id"]]}
        for r in _read_csv(dir / "labels.csv")
        if r["unit_id"] in predictions
    ]
    typer.echo(markdown_table(score(rows)))
    typer.echo(f"unlabelled: {sum(1 for r in rows if r['label'] not in ('1', '0'))}")


def main() -> None:
    app()
