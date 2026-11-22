"""Chuẩn bị thư mục dữ liệu và cấu hình. API gọi lúc khởi động nên không cần lệnh cài riêng."""

import shutil
from pathlib import Path

from h4wk.core.db import get_engine


def init_workspace(data_dir: Path, config_dir: Path) -> list[Path]:
    """Tạo thư mục dữ liệu và chép config/*.toml.example thành *.toml nếu chưa có.

    Không ghi đè file *.toml đã có vì đó là cấu hình thật của từng máy. Không thêm đối tượng
    hay kênh nào. Trả về danh sách file cấu hình vừa tạo.
    """
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
