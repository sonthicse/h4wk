import json
from datetime import datetime

from sqlmodel import Session

from h4wk.core.db import WatchItemRow, get_engine
from h4wk.core.entities import load_entities
from h4wk.core.types import VN_TZ
from h4wk.core.workspace import init_workspace
from h4wk.watchlist import service


def test_init_adds_no_entity_or_channel(data_dir, config_dir):
    """Khởi tạo không tự thêm đối tượng hay kênh: ai dùng cũng tự khai báo của mình."""
    init_workspace(data_dir, config_dir)
    assert load_entities() == [] and service.load_channels() == []


def test_init_moves_old_entities_and_watchlist_to_config(data_dir, config_dir):
    """Máy đang chạy bản cũ: đối tượng ở data/entities.json, kênh chỉ ở database."""
    data_dir.mkdir(parents=True)
    old = [{"id": "e_01", "name": "Nguyễn Văn A", "aliases": ["Ông A"], "abbreviations": []}]
    (data_dir / "entities.json").write_text(json.dumps(old), encoding="utf-8")
    with Session(get_engine(data_dir)) as s:
        s.add(
            WatchItemRow(
                id="w_002",
                channel_id="UC123",
                handle="@kenh",
                title="Kênh",
                level="metadata",
                initialized=True,
                created_at=datetime(2026, 11, 1, tzinfo=VN_TZ),
            )
        )
        s.commit()

    for _ in range(2):
        init_workspace(data_dir, config_dir)

    assert (config_dir / "entities.toml").is_file()
    assert not (data_dir / "entities.json").exists()
    assert (data_dir / "entities.json.migrated").is_file()
    assert [(e.id, e.aliases) for e in load_entities()] == [("e_01", ["Ông A"])]
    assert (config_dir / "watchlist.toml").is_file()
    [channel] = service.load_channels()
    assert (channel.id, channel.channel_id, channel.level) == ("w_002", "UC123", "metadata")
    # Trạng thái chạy giữ nguyên trong database, không phải khởi tạo lại.
    assert service.get_item("w_002").initialized
