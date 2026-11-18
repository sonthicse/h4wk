"""Fixture dùng chung: mỗi test có thư mục dữ liệu riêng."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "data"
    monkeypatch.setenv("H4WK_DATA_DIR", str(d))
    return d


@pytest.fixture
def client(data_dir: Path) -> Iterator[TestClient]:
    from h4wk.api.app import app

    with TestClient(app) as c:
        yield c
