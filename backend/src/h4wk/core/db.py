"""Database chỉ mục SQLite (chế độ WAL) trong data/index.db. File trong data/ là nguồn gốc;
database chỉ để tra cứu nhanh và dựng lại được (T45)."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import Field, Session, SQLModel, create_engine

from h4wk.core.config import data_dir
from h4wk.core.types import VN_TZ


class CaseRow(SQLModel, table=True):
    __tablename__ = "cases"
    id: str = Field(primary_key=True)
    title: str
    created_at: datetime


class EntityRow(SQLModel, table=True):
    __tablename__ = "entities"
    case_id: str = Field(primary_key=True, foreign_key="cases.id")
    id: str = Field(primary_key=True)
    name: str


class UserRow(SQLModel, table=True):
    __tablename__ = "users"
    username: str = Field(primary_key=True)
    password_hash: str  # argon2
    created_at: datetime


class SessionRow(SQLModel, table=True):
    __tablename__ = "sessions"
    token_hash: str = Field(primary_key=True)  # SHA-256 của token trong cookie
    username: str = Field(foreign_key="users.username")
    expires_at: datetime


class SourceStateRow(SQLModel, table=True):
    """Tình trạng nguồn thu, dùng chung giữa các worker."""

    __tablename__ = "source_state"
    provider: str = Field(primary_key=True)
    consecutive_failures: int = 0
    suspended_until: datetime | None = None


class JobRow(SQLModel, table=True):
    """Một lần chạy luồng collect → media → analyze cho một video."""

    __tablename__ = "jobs"
    id: str = Field(primary_key=True)
    case_id: str = Field(foreign_key="cases.id", index=True)
    target: str
    video_id: str
    level: str
    force: bool = False
    trigger: str  # user:<username> hoặc system:<rule>
    status: str = "queued"  # queued | running | done | failed
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
    case_id: str = Field(foreign_key="cases.id", index=True)
    video_id: str
    capture: str
    run_id: str
    data: str


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

        SQLModel.metadata.create_all(engine)
        _engines[path] = engine
    return _engines[path]


def as_aware(dt: datetime) -> datetime:
    """SQLite không lưu múi giờ; SQLAlchemy lưu giờ UTC. Đọc ra luôn đổi về giờ Việt Nam."""
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).astimezone(VN_TZ)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
