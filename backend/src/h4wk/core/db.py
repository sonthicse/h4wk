"""Database chỉ mục SQLite (chế độ WAL) trong data/index.db. File trong data/ là nguồn gốc;
database chỉ để tra cứu nhanh và dựng lại được (T45)."""

from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import Field, Session, SQLModel, create_engine

from h4wk.core.config import data_dir


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


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
