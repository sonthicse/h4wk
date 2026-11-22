from pathlib import Path

from h4wk.core.config import REPO_ROOT, data_dir


def test_data_dir_defaults_to_repo_data(dotenv) -> None:
    del dotenv["H4WK_DATA_DIR"]
    assert data_dir() == REPO_ROOT / "data"


def test_data_dir_reads_dotenv(dotenv, tmp_path: Path, monkeypatch) -> None:
    dotenv["H4WK_DATA_DIR"] = str(tmp_path / "x")
    monkeypatch.setenv("H4WK_DATA_DIR", "/khong-dung")  # biến môi trường không được tính
    assert data_dir() == tmp_path / "x"
