from dataclasses import dataclass
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.db import SessionLocal


@dataclass(frozen=True)
class RequestContext:
    tenant_id: UUID
    actor_user_id: UUID


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def get_request_context(
    tenant_id: Annotated[UUID | None, Header(alias="X-Tenant-Id")] = None,
    actor_user_id: Annotated[UUID | None, Header(alias="X-Actor-User-Id")] = None,
) -> RequestContext:
    if tenant_id is None or actor_user_id is None:
        raise AppError(status_code=401, code="missing_context", message="Tenant and actor headers are required")
    return RequestContext(tenant_id=tenant_id, actor_user_id=actor_user_id)
