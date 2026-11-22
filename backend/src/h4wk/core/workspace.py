import shutil
from pathlib import Path

from h4wk.core.db import get_engine


def init_workspace(data_dir: Path, config_dir: Path) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    get_engine(data_dir)
    from h4wk.core.entities import migrate_legacy as migrate_entities
    from h4wk.watchlist.service import migrate_legacy as migrate_watchlist

    migrate_entities()
    migrate_watchlist()
    created: list[Path] = []
    for example in sorted(config_dir.glob("*.toml.example")):
        target = example.with_suffix("")
        if not target.exists():
            shutil.copyfile(example, target)
            created.append(target)
    return created
