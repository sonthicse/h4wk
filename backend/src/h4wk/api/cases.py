"""API case và đối tượng (T6). Mọi thao tác ghi đều để lại dòng audit, kể cả khi lỗi."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session

from h4wk.api.deps import current_actor
from h4wk.core import audit, cases
from h4wk.core.db import get_session

router = APIRouter(prefix="/api/cases", tags=["cases"])
SessionDep = Annotated[Session, Depends(get_session)]
ActorDep = Annotated[str, Depends(current_actor)]


class CaseCreate(BaseModel):
    title: str = Field(min_length=1)
    goal: str = ""


class EntityCreate(BaseModel):
    name: str = Field(min_length=1)
    aliases: list[str] = []
    abbreviations: list[str] = []


class CaseSummary(BaseModel):
    id: str
    title: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_case(body: CaseCreate, session: SessionDep, actor: ActorDep) -> cases.CaseFile:
    try:
        case = cases.create_case(session, title=body.title, goal=body.goal, owner=actor)
    except Exception as e:
        audit.log(None, actor, "case.create", None, {"error": str(e)}, status="error")
        raise
    audit.log(case.id, actor, "case.create", case.id, {"title": case.title})
    return case


@router.get("")
def list_cases(session: SessionDep) -> list[CaseSummary]:
    return [CaseSummary(id=r.id, title=r.title) for r in cases.list_cases(session)]


@router.get("/{case_id}")
def get_case(case_id: str) -> cases.CaseFile:
    try:
        return cases.load_case(case_id)
    except cases.NotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found") from None


@router.post("/{case_id}/entities", status_code=status.HTTP_201_CREATED)
def add_entity(
    case_id: str, body: EntityCreate, session: SessionDep, actor: ActorDep
) -> cases.Entity:
    try:
        entity = cases.add_entity(session, case_id, **body.model_dump())
    except cases.NotFound:
        audit.log(None, actor, "entity.create", case_id, {"error": "case not found"}, "error")
        raise HTTPException(status.HTTP_404_NOT_FOUND, "case not found") from None
    except Exception as e:
        audit.log(case_id, actor, "entity.create", None, {"error": str(e)}, status="error")
        raise
    audit.log(case_id, actor, "entity.create", entity.id, {"name": entity.name})
    return entity
