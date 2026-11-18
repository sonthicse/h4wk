"""CLI `h4wk`."""

import shutil
from pathlib import Path

import typer

from h4wk.core.config import CONFIG_DIR, data_dir

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


def main() -> None:
    app()
