from pathlib import Path

from h4wk.cli import init_workspace


def _make_examples(config_dir: Path) -> None:
    config_dir.mkdir()
    (config_dir / "sources.toml.example").write_text("# mẫu sources\n")
    (config_dir / "ai.toml.example").write_text("# mẫu ai\n")


def test_init_creates_data_dir(tmp_path: Path) -> None:
    _make_examples(tmp_path / "config")
    data_dir = tmp_path / "data"
    init_workspace(data_dir=data_dir, config_dir=tmp_path / "config")
    assert data_dir.is_dir()


def test_init_copies_examples_to_toml(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _make_examples(config_dir)
    init_workspace(data_dir=tmp_path / "data", config_dir=config_dir)
    assert (config_dir / "sources.toml").read_text() == "# mẫu sources\n"
    assert (config_dir / "ai.toml").read_text() == "# mẫu ai\n"


def test_init_does_not_overwrite_existing_toml(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _make_examples(config_dir)
    (config_dir / "ai.toml").write_text("# cấu hình thật\n")
    init_workspace(data_dir=tmp_path / "data", config_dir=config_dir)
    assert (config_dir / "ai.toml").read_text() == "# cấu hình thật\n"
