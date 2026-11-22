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
    get_engine(data_dir)  # tạo database chỉ mục nếu chưa có
    # Chuyển đối tượng và watchlist từ chỗ lưu cũ (data/, database) sang config/ trước khi chép
    # file mẫu, để file mẫu rỗng không đè mất dữ liệu cũ.
    from h4wk.core.entities import migrate_legacy as migrate_entities
    from h4wk.watchlist.service import migrate_legacy as migrate_watchlist

    migrate_entities()
    migrate_watchlist()
    created: list[Path] = []
    for example in sorted(config_dir.glob("*.toml.example")):
        target = example.with_suffix("")  # bỏ đuôi .example
        if not target.exists():
            shutil.copyfile(example, target)
            created.append(target)
    return created
