"""Database chỉ mục SQLite (chế độ WAL) trong data/index.db. File trong data/ là nguồn gốc;
database chỉ để tra cứu nhanh và dựng lại được (T45)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from sqlalchemy import Engine, event
from sqlmodel import Field, Session, SQLModel, create_engine

from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ

if TYPE_CHECKING:
    from h4wk.analysis.models import Finding


class EntityRow(SQLModel, table=True):
    __tablename__ = "entities"
    id: str = Field(primary_key=True)
    name: str


class SessionRow(SQLModel, table=True):
    __tablename__ = "sessions"
    token_hash: str = Field(primary_key=True)  # SHA-256 của token trong cookie
    username: str
    expires_at: datetime


class SourceStateRow(SQLModel, table=True):
    """Tình trạng nguồn thu, dùng chung giữa các worker."""

    __tablename__ = "source_state"
    provider: str = Field(primary_key=True)
    consecutive_failures: int = 0
    suspended_until: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


class QuotaRow(SQLModel, table=True):
    """Quota đã dùng của nguồn thu trong kỳ hiện tại (YouTube API: một ngày theo giờ Pacific)."""

    __tablename__ = "source_quota"
    provider: str = Field(primary_key=True)
    period: str  # "2026-11-19": ngày theo giờ Pacific
    used: int = 0


class JobRow(SQLModel, table=True):
    """Một lần chạy luồng collect → media → analyze cho một video."""

    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    target: str
    video_id: str
    level: str
    force: bool = False
    trigger: str  # user:<username> hoặc system:<rule>
    status: str = "queued"  # waiting | queued | running | done | failed (waiting: xem lanes.py)
    step: str | None = None  # collect | media | analyze
    progress: int = 0
    capture: str | None = None
    run_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class FindingRow(SQLModel, table=True):
    """Chỉ mục nghi vấn; nội dung đầy đủ nằm ở findings.json, ở đây giữ bản sao JSON."""

    __tablename__ = "findings"
    id: str = Field(primary_key=True)
    video_id: str
    capture: str
    run_id: str
    data: str


def finding_row(f: "Finding") -> FindingRow:
    """Dòng chỉ mục của một nghi vấn (dùng khi phân tích)."""
    return FindingRow(
        id=f.id,
        video_id=f.video_id,
        capture=f.capture,
        run_id=f.run_id,
        data=f.model_dump_json(),
    )


class DecisionRow(SQLModel, table=True):
    """Chỉ mục quyết định rà soát; nguồn gốc là reviews.jsonl (chỉ ghi thêm)."""

    __tablename__ = "decisions"
    id: int | None = Field(default=None, primary_key=True)
    finding_id: str = Field(index=True)
    data: str


class VideoDecisionRow(SQLModel, table=True):
    __tablename__ = "video_decisions"
    id: int | None = Field(default=None, primary_key=True)
    video_id: str = Field(index=True)
    run_id: str
    data: str


class WatchItemRow(SQLModel, table=True):
    """Một kênh trong watchlist. initialized=False: chưa chạy bước thêm kênh (SPEC 10.9)."""

    __tablename__ = "watch_items"
    id: str = Field(primary_key=True)  # w_001
    channel_id: str = Field(index=True)
    handle: str | None = None
    title: str = ""
    enabled: bool = True
    level: str = "full"
    initialized: bool = False
    created_at: datetime
    last_checked_at: datetime | None = None
    last_error: str | None = None


class KnownVideoRow(SQLModel, table=True):
    """Video đã biết của một mục watchlist; video mới là video chưa có ở đây."""

    __tablename__ = "known_videos"
    watch_item: str = Field(primary_key=True)
    video_id: str = Field(primary_key=True)
    title: str = ""
    published_at: datetime | None = None
    first_seen_at: datetime


class EventRow(SQLModel, table=True):
    """Dòng sự kiện trên dashboard: new_video, channel_added, job_done, job_failed."""

    __tablename__ = "events"
    id: int | None = Field(default=None, primary_key=True)
    at: datetime = Field(index=True)
    kind: str
    message: str
    watch_item: str | None = None
    video_id: str | None = None
    job_id: str | None = None


_engines: dict[Path, Engine] = {}


def get_engine(root: Path | None = None) -> Engine:
    path = ((root or data_dir()) / "index.db").resolve()
    if path not in _engines:
        path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{path}")

        @event.listens_for(engine, "connect")
        def _pragmas(conn: object, _record: object) -> None:
            cur = conn.cursor()  # type: ignore[attr-defined]
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

        _drop_legacy_accounts(engine)
        SQLModel.metadata.create_all(engine)
        _add_missing_columns(engine)
        _engines[path] = engine
    return _engines[path]


def _drop_legacy_accounts(engine: Engine) -> None:
    """Index cũ có bảng users (nhiều tài khoản) và sessions trỏ khoá ngoại tới đó. Nay chỉ còn
    một tài khoản lấy từ .env: bỏ hai bảng cũ, sessions được tạo lại (phải đăng nhập lại)."""
    with engine.begin() as conn:
        tables = {r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master")}
        if "users" in tables:
            conn.exec_driver_sql("DROP TABLE IF EXISTS sessions")
            conn.exec_driver_sql("DROP TABLE users")


def _add_missing_columns(engine: Engine) -> None:
    """create_all không thêm cột mới vào bảng đã có. Cột mới luôn cho phép NULL nên thêm
    bằng ALTER TABLE là đủ; chỉ mục dựng lại được từ data/ nên không cần công cụ migrate."""
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            have = {r[1] for r in conn.exec_driver_sql(f'PRAGMA table_info("{table.name}")')}
            for column in table.columns:
                if column.name not in have:
                    ddl = column.type.compile(dialect=engine.dialect)
                    conn.exec_driver_sql(
                        f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {ddl}'
                    )


def as_aware(dt: datetime) -> datetime:
    """SQLite không lưu múi giờ; SQLAlchemy lưu giờ UTC. Đọc ra luôn đổi về giờ Việt Nam."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(VN_TZ)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
