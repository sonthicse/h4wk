"""Đối tượng cần bảo vệ. entities.json là nguồn gốc; database chỉ mục được cập nhật theo."""

from pathlib import Path

from pydantic import Field, TypeAdapter
from sqlmodel import Session

from h4wk.core.config import data_dir
from h4wk.core.db import EntityRow
from h4wk.core.types import Contract


class Entity(Contract):
    """Đối tượng cần bảo vệ. Ảnh mẫu nằm ở entities/<id>/refs/{face,image}/."""

    id: str = Field(pattern=r"^e_\d{2,}$")
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []


_ENTITIES = TypeAdapter(list[Entity])


def entities_file() -> Path:
    return data_dir() / "entities.json"


def load_entities() -> list[Entity]:
    path = entities_file()
    if not path.is_file():
        return []
    return _ENTITIES.validate_json(path.read_text(encoding="utf-8"))


def _save(entities: list[Entity]) -> None:
    path = entities_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(_ENTITIES.dump_json(entities, indent=2).decode("utf-8"), encoding="utf-8")
    tmp.replace(path)


def add_entity(
    session: Session, *, name: str, aliases: list[str], abbreviations: list[str]
) -> Entity:
    entities = load_entities()
    entity = Entity(
        id=f"e_{len(entities) + 1:02d}",
        name=name,
        aliases=aliases,
        abbreviations=abbreviations,
    )
    entities.append(entity)
    _save(entities)
    session.add(EntityRow(id=entity.id, name=entity.name))
    session.commit()
    return entity
