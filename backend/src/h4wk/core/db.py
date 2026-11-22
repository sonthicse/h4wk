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
    token_hash: str = Field(primary_key=True)
    username: str
    expires_at: datetime


class SourceStateRow(SQLModel, table=True):
    __tablename__ = "source_state"
    provider: str = Field(primary_key=True)
    consecutive_failures: int = 0
    suspended_until: datetime | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


class QuotaRow(SQLModel, table=True):
    __tablename__ = "source_quota"
    provider: str = Field(primary_key=True)
    period: str
    used: int = 0


class JobRow(SQLModel, table=True):
    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    target: str
    video_id: str
    level: str
    force: bool = False
    trigger: str
    status: str = "queued"
    step: str | None = None
    progress: int = 0
    capture: str | None = None
    run_id: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class FindingRow(SQLModel, table=True):
    __tablename__ = "findings"
    id: str = Field(primary_key=True)
    video_id: str
    capture: str
    run_id: str
    data: str


def finding_row(f: "Finding") -> FindingRow:
    return FindingRow(
        id=f.id,
        video_id=f.video_id,
        capture=f.capture,
        run_id=f.run_id,
        data=f.model_dump_json(),
    )


class DecisionRow(SQLModel, table=True):
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
    __tablename__ = "watch_items"
    id: str = Field(primary_key=True)
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
    __tablename__ = "known_videos"
    watch_item: str = Field(primary_key=True)
    video_id: str = Field(primary_key=True)
    title: str = ""
    published_at: datetime | None = None
    first_seen_at: datetime


class EventRow(SQLModel, table=True):
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
    with engine.begin() as conn:
        tables = {r[0] for r in conn.exec_driver_sql("SELECT name FROM sqlite_master")}
        if "users" in tables:
            conn.exec_driver_sql("DROP TABLE IF EXISTS sessions")
            conn.exec_driver_sql("DROP TABLE users")


def _add_missing_columns(engine: Engine) -> None:
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
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(VN_TZ)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
