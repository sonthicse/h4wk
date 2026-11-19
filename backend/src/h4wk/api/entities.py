"""API đối tượng (T6). Mọi thao tác ghi đều để lại dòng audit, kể cả khi lỗi."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from h4wk.api.deps import current_actor
from h4wk.core import audit, entities
from h4wk.core.db import get_session

router = APIRouter(prefix="/api/entities", tags=["entities"])
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[str, Depends(current_actor)]


class EntityCreate(BaseModel):
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []


@router.get("")
def list_entities() -> list[entities.Entity]:
    return entities.load_entities()


@router.post("", status_code=status.HTTP_201_CREATED)
def add_entity(body: EntityCreate, session: SessionDep, actor: ActorDep) -> entities.Entity:
    try:
        entity = entities.add_entity(session, **body.model_dump())
    except Exception as e:
        audit.log(actor, "entity.create", None, {"error": str(e)}, status="error")
        raise
    audit.log(actor, "entity.create", entity.id, {"name": entity.name})
    return entity
