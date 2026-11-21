import pytest
from sqlmodel import Session
from typer.testing import CliRunner

from h4wk.cli import app
from h4wk.core.db import get_engine
from h4wk.core.entities import add_entity, load_entities


@pytest.mark.parametrize("existing", [False, True])
def test_init_seeds_entity_only_when_empty(data_dir, existing):
    if existing:
        with Session(get_engine(data_dir)) as session:
            add_entity(session, name="Đối tượng có sẵn", aliases=[], abbreviations=[])
    expected = "Đối tượng có sẵn" if existing else "Đảng và Nhà nước Việt Nam"
    cli = CliRunner()
    for _ in range(2):
        result = cli.invoke(app, ["init"])
        assert result.exit_code == 0, result.exception
        assert [e.name for e in load_entities()] == [expected]
