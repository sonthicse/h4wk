import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, TypeAdapter
from sqlmodel import Session

from h4wk.core import tomlw
from h4wk.core.config import config_dir, data_dir
from h4wk.core.config_models import load_toml
from h4wk.core.db import EntityRow
from h4wk.core.types import VN_TZ, Contract, VnDatetime


class Entity(Contract):
    id: str = Field(pattern=r"^e_\d{2,}$")
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []
    description: str | None = None


def _unique_ids(items: list[Entity]) -> list[Entity]:
    ids = [e.id for e in items]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate entity id")
    return items


class EntitiesConfig(Contract):
    entities: Annotated[list[Entity], AfterValidator(_unique_ids)] = []


def entities_file() -> Path:
    return config_dir() / "entities.toml"


def _legacy_file() -> Path:
    return data_dir() / "entities.json"


def migrate_legacy() -> bool:
    old = _legacy_file()
    if entities_file().exists() or not old.is_file():
        return False
    items = TypeAdapter(list[Entity]).validate_python(json.loads(old.read_text(encoding="utf-8")))
    _save(items)
    old.replace(old.with_name("entities.json.migrated"))
    return True


def load_entities() -> list[Entity]:
    migrate_legacy()
    path = entities_file()
    if not path.is_file():
        return []
    return load_toml(path, EntitiesConfig).entities


def _save(entities: list[Entity]) -> None:
    path = entities_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = EntitiesConfig(entities=entities).model_dump(mode="json")
    tmp = path.with_suffix(".toml.tmp")
    tmp.write_text(tomlw.dumps(data), encoding="utf-8")
    tmp.replace(path)


def add_entity(
    session: Session,
    *,
    name: str,
    aliases: list[str],
    abbreviations: list[str],
    description: str | None = None,
) -> Entity:
    entities = load_entities()
    entity = Entity(
        id=f"e_{len(entities) + 1:02d}",
        name=name,
        aliases=aliases,
        abbreviations=abbreviations,
        description=description,
    )
    entities.append(entity)
    _save(entities)
    session.add(EntityRow(id=entity.id, name=entity.name))
    session.commit()
    return entity


class NotFound(LookupError):
    pass


class TooLarge(ValueError):
    pass


def get_entity(entity_id: str) -> Entity:
    for entity in load_entities():
        if entity.id == entity_id:
            return entity
    raise NotFound(entity_id)


def update_entity(session: Session, entity_id: str, **fields: object) -> Entity:
    entities = load_entities()
    for i, entity in enumerate(entities):
        if entity.id == entity_id:
            entities[i] = Entity.model_validate({**entity.model_dump(), **fields})
            _save(entities)
            row = session.get(EntityRow, entity_id)
            if row is None:
                row = EntityRow(id=entity_id, name=entities[i].name)
            row.name = entities[i].name
            session.add(row)
            session.commit()
            return entities[i]
    raise NotFound(entity_id)


RefKind = Literal["face", "image"]
MAX_REF_BYTES = 10 * 1024 * 1024
REF_FILE = re.compile(r"^[0-9a-f]{16}\.(jpg|png|webp)$")
_MAGIC = {b"\xff\xd8\xff": "jpg", b"\x89PNG\r\n\x1a\n": "png"}


class RefImage(Contract):
    kind: RefKind
    file: str
    bytes: int
    sha256: str
    uploaded_at: VnDatetime
    url: str


def refs_dir(entity_id: str, kind: RefKind) -> Path:
    return data_dir() / "entities" / entity_id / "refs" / kind


def _image_ext(data: bytes) -> str | None:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    for magic, ext in _MAGIC.items():
        if data.startswith(magic):
            return ext
    return None


def _ref(entity_id: str, kind: RefKind, path: Path) -> RefImage:
    data = path.read_bytes()
    return RefImage(
        kind=kind,
        file=path.name,
        bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        uploaded_at=datetime.fromtimestamp(path.stat().st_mtime, VN_TZ),
        url=f"/api/entities/{entity_id}/refs/{kind}/{path.name}",
    )


def list_refs(entity_id: str) -> dict[str, list[RefImage]]:
    get_entity(entity_id)
    out: dict[str, list[RefImage]] = {}
    for kind in ("face", "image"):
        d = refs_dir(entity_id, kind)
        files = sorted(p for p in d.iterdir() if REF_FILE.match(p.name)) if d.is_dir() else []
        out[kind] = [_ref(entity_id, kind, p) for p in files]
    return out


def add_ref(entity_id: str, kind: RefKind, data: bytes) -> RefImage:
    get_entity(entity_id)
    if len(data) > MAX_REF_BYTES:
        raise TooLarge(f"image is larger than {MAX_REF_BYTES // (1024 * 1024)} MB")
    ext = _image_ext(data)
    if ext is None:
        raise ValueError("only JPEG, PNG or WebP images are accepted")
    d = refs_dir(entity_id, kind)
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{hashlib.sha256(data).hexdigest()[:16]}.{ext}"
    if not path.exists():
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    return _ref(entity_id, kind, path)


def ref_path(entity_id: str, kind: RefKind, file: str) -> Path:
    get_entity(entity_id)
    path = refs_dir(entity_id, kind) / file
    if not REF_FILE.match(file) or not path.is_file():
        raise NotFound(f"{entity_id}/{kind}/{file}")
    return path


def ref_counts(entity_id: str) -> dict[str, int]:
    return {
        kind: sum(1 for p in d.iterdir() if REF_FILE.match(p.name)) if d.is_dir() else 0
        for kind in ("face", "image")
        for d in [refs_dir(entity_id, kind)]
    }


def delete_ref(entity_id: str, kind: RefKind, file: str) -> None:
    ref_path(entity_id, kind, file).unlink()
