import os
import sqlite3
import tomllib
from pathlib import Path

from h4wk.core import secrets, settings, tomlw
from h4wk.core.config_models import SourcesConfig, load_toml

REPO_CONFIG = Path(__file__).parents[3] / "config"


def test_toml_round_trip_of_examples(tmp_path: Path) -> None:
    for name, model in [("sources", SourcesConfig)]:
        cfg = load_toml(REPO_CONFIG / f"{name}.toml.example", model)
        text = tomlw.dumps(cfg.model_dump(mode="json", exclude_none=True, by_alias=True))
        assert model.model_validate(tomllib.loads(text)) == cfg


def test_save_and_load_sources(config_dir: Path) -> None:
    cfg = SourcesConfig.model_validate({"priority": {"video.metadata": ["ytdlp"]}})
    settings.save_sources(cfg)
    assert settings.load_sources() == cfg
    assert (config_dir / "sources.toml").is_file()


def test_secrets_file_is_0600_and_wins_over_env(data_dir: Path, dotenv) -> None:
    dotenv["YOUTUBE_API_KEY"] = "from-env-1234567890"
    assert secrets.info("YOUTUBE_API_KEY").origin == "env"
    secrets.put("YOUTUBE_API_KEY", "AIzaSyFromSettings0000abcd")
    assert os.stat(data_dir / "secrets.json").st_mode & 0o777 == 0o600
    assert secrets.get("YOUTUBE_API_KEY") == "AIzaSyFromSettings0000abcd"
    info = secrets.info("YOUTUBE_API_KEY")
    assert info.origin == "settings" and info.masked == "AIza…abcd"
    secrets.delete("YOUTUBE_API_KEY")
    assert secrets.info("YOUTUBE_API_KEY").origin == "env"


def test_new_column_is_added_to_old_index(data_dir: Path) -> None:
    data_dir.mkdir(parents=True)
    con = sqlite3.connect(data_dir / "index.db")
    con.execute("CREATE TABLE source_state (provider TEXT PRIMARY KEY, consecutive_failures INT)")
    con.commit()
    con.close()
    from h4wk.core.db import get_engine

    get_engine(data_dir)
    cols = {
        r[1]
        for r in sqlite3.connect(data_dir / "index.db").execute("PRAGMA table_info(source_state)")
    }
    assert {"last_error", "last_error_at", "suspended_until"} <= cols
