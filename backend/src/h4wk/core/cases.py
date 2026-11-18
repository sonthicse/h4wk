"""Case và đối tượng. case.json là nguồn gốc; database chỉ mục được cập nhật theo."""

from datetime import datetime
from pathlib import Path

from pydantic import Field
from sqlmodel import Session, select

from h4wk.core.config import data_dir
from h4wk.core.db import CaseRow, EntityRow
from h4wk.core.types import VN_TZ, Actor, Contract, VnDatetime


class Entity(Contract):
    """Đối tượng cần bảo vệ. Ảnh mẫu nằm ở entities/<id>/refs/{face,image}/."""

    id: str = Field(pattern=r"^e_\d{2,}$")
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []


class CaseFile(Contract):
    """Nội dung case.json."""

    id: str = Field(pattern=r"^\d{4}-\d{2}_case-\d{4,}$")
    title: str = Field(min_length=1)
    goal: str = ""
    owner: Actor
    created_at: VnDatetime
    entities: list[Entity] = []


class NotFound(LookupError):
    pass


def case_dir(case_id: str) -> Path:
    return data_dir() / "cases" / case_id


def _save(case: CaseFile) -> None:
    d = case_dir(case.id)
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "case.json.tmp"
    tmp.write_text(case.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(d / "case.json")


def load_case(case_id: str) -> CaseFile:
    path = case_dir(case_id) / "case.json"
    if not path.is_file():
        raise NotFound(case_id)
    return CaseFile.model_validate_json(path.read_text(encoding="utf-8"))


def create_case(session: Session, *, title: str, goal: str, owner: str) -> CaseFile:
    now = datetime.now(VN_TZ)
    n = len(session.exec(select(CaseRow.id)).all()) + 1
    case = CaseFile(
        id=f"{now:%Y-%m}_case-{n:04d}", title=title, goal=goal, owner=owner, created_at=now
    )
    _save(case)
    session.add(CaseRow(id=case.id, title=case.title, created_at=now))
    session.commit()
    return case


def list_cases(session: Session) -> list[CaseRow]:
    return list(session.exec(select(CaseRow).order_by(CaseRow.id)).all())


def add_entity(
    session: Session, case_id: str, *, name: str, aliases: list[str], abbreviations: list[str]
) -> Entity:
    case = load_case(case_id)
    entity = Entity(
        id=f"e_{len(case.entities) + 1:02d}",
        name=name,
        aliases=aliases,
        abbreviations=abbreviations,
    )
    case.entities.append(entity)
    _save(case)
    session.add(EntityRow(case_id=case_id, id=entity.id, name=entity.name))
    session.commit()
    return entity
