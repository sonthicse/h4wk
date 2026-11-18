"""CLI `h4wk`."""

import json
import shutil
from pathlib import Path

import typer
from pydantic import TypeAdapter

from h4wk.analysis.models import EntityHit, Finding, ReviewDecision
from h4wk.collectors.models import Normalized
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


@app.command()
def verify(capture_dir: Path) -> None:
    """Kiểm tra toàn vẹn một bản thu: tính lại SHA-256 từng file và so với manifest."""
    results = verify_capture(capture_dir)
    for r in results:
        typer.echo(f"{r.status.value:<10} {r.path}")
    if any(r.status != FileStatus.OK for r in results):
        raise typer.Exit(code=1)


def main() -> None:
    app()
