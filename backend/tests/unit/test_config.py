from pathlib import Path

import pytest

from h4wk.core.config import REPO_ROOT, data_dir


def test_data_dir_defaults_to_repo_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("H4WK_DATA_DIR", raising=False)
    assert data_dir() == REPO_ROOT / "data"


def test_data_dir_reads_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("H4WK_DATA_DIR", str(tmp_path / "x"))
    assert data_dir() == tmp_path / "x"
