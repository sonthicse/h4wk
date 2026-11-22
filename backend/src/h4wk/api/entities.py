from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlmodel import Session

from h4wk.api.deps import current_actor
from h4wk.core import audit, entities
from h4wk.core.db import get_session
from h4wk.core.entities import RefKind

router = APIRouter(prefix="/api/entities", tags=["entities"])
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[str, Depends(current_actor)]


class EntityCreate(BaseModel):
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []
    description: str | None = None


class EntityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    aliases: list[str] | None = None
    abbreviations: list[str] | None = None
    description: str | None = None


def _blank_to_none(fields: dict) -> dict:
    if "description" in fields:
        fields["description"] = (fields["description"] or "").strip() or None
    return fields


def _not_found(actor: str, action: str, target: str) -> HTTPException:
    audit.log(actor, action, target, {"error": "not found"}, status="error")
    return HTTPException(status.HTTP_404_NOT_FOUND, "entity or image not found")


class RefCounts(BaseModel):
    face: int
    image: int


class EntityOut(entities.Entity):
    ref_counts: RefCounts


@router.get("")
def list_entities() -> list[EntityOut]:
    return [
        EntityOut(**e.model_dump(), ref_counts=RefCounts(**entities.ref_counts(e.id)))
        for e in entities.load_entities()
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
def add_entity(body: EntityCreate, session: SessionDep, actor: ActorDep) -> entities.Entity:
    try:
        entity = entities.add_entity(session, **_blank_to_none(body.model_dump()))
    except Exception as e:
        audit.log(actor, "entity.create", None, {"error": str(e)}, status="error")
        raise
    audit.log(actor, "entity.create", entity.id, {"name": entity.name})
    return entity


@router.patch("/{entity_id}")
def update_entity(
    entity_id: str, body: EntityUpdate, session: SessionDep, actor: ActorDep
) -> entities.Entity:
    fields = {
        k: v
        for k, v in body.model_dump(exclude_unset=True).items()
        if v is not None or k == "description"
    }
    fields = _blank_to_none(fields)
    try:
        entity = entities.update_entity(session, entity_id, **fields)
    except entities.NotFound:
        raise _not_found(actor, "entity.update", entity_id) from None
    except Exception as e:
        audit.log(actor, "entity.update", entity_id, {"error": str(e)}, status="error")
        raise
    audit.log(actor, "entity.update", entity_id, fields)
    return entity


@router.get("/{entity_id}/refs")
def list_refs(entity_id: str) -> dict[RefKind, list[entities.RefImage]]:
    try:
        return entities.list_refs(entity_id)  # type: ignore[return-value]
    except entities.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "entity not found") from None


@router.post(
    "/{entity_id}/refs/{kind}",
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                t: {"schema": {"type": "string", "format": "binary"}}
                for t in ("image/jpeg", "image/png", "image/webp")
            },
        }
    },
)
async def add_ref(
    entity_id: str, kind: RefKind, request: Request, actor: ActorDep
) -> entities.RefImage:
    target = f"{entity_id}/{kind}"
    data = await request.body()
    try:
        ref = entities.add_ref(entity_id, kind, data)
    except entities.NotFound:
        raise _not_found(actor, "entity.ref.add", target) from None
    except entities.TooLarge as e:
        audit.log(actor, "entity.ref.add", target, {"error": str(e)}, status="error")
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(e)) from None
    except ValueError as e:
        audit.log(actor, "entity.ref.add", target, {"error": str(e)}, status="error")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from None
    audit.log(actor, "entity.ref.add", f"{target}/{ref.file}", {"sha256": ref.sha256})
    return ref


@router.get("/{entity_id}/refs/{kind}/{file}", response_class=FileResponse)
def get_ref(entity_id: str, kind: RefKind, file: str) -> FileResponse:
    try:
        return FileResponse(entities.ref_path(entity_id, kind, file))
    except entities.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "image not found") from None


@router.delete("/{entity_id}/refs/{kind}/{file}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ref(entity_id: str, kind: RefKind, file: str, actor: ActorDep) -> Response:
    target = f"{entity_id}/{kind}/{file}"
    try:
        entities.delete_ref(entity_id, kind, file)
    except entities.NotFound:
        raise _not_found(actor, "entity.ref.delete", target) from None
    audit.log(actor, "entity.ref.delete", target)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
