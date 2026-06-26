from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import RequestContext, get_request_context, get_session
from app.schemas import ActivityCreate, ActivityListItem, ActivityResponse, MemberUnread
from app.services import ActivityService

router = APIRouter(tags=["project-activity"])


@router.get("/projects/{project_id}/activity", response_model=list[ActivityListItem])
async def list_project_activity(
    project_id: Annotated[UUID, Path()],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    session: AsyncSession = Depends(get_session),
    context: RequestContext = Depends(get_request_context),
):
    service = ActivityService(session)
    return await service.list_activity(project_id, context, limit)


@router.post("/projects/{project_id}/activity-events", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_project_activity(
    project_id: Annotated[UUID, Path()],
    payload: ActivityCreate,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    session: AsyncSession = Depends(get_session),
    context: RequestContext = Depends(get_request_context),
):
    service = ActivityService(session)
    return await service.create_activity(project_id, payload, context, idempotency_key)


@router.get("/projects/{project_id}/unread", response_model=list[MemberUnread])
async def get_project_unread(
    project_id: Annotated[UUID, Path()],
    session: AsyncSession = Depends(get_session),
    context: RequestContext = Depends(get_request_context),
):
    service = ActivityService(session)
    return await service.get_unread(project_id, context)
