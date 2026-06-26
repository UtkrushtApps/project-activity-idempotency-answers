from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.dependencies import RequestContext
from app.repositories import ActivityRepository
from app.schemas import ActivityCreate, ActivityListItem, ActivityResponse, ActorSummary, MemberUnread


class ActivityService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ActivityRepository(session)

    async def list_activity(self, project_id: UUID, context: RequestContext, limit: int) -> list[ActivityListItem]:
        await self._ensure_project_member(project_id, context)
        rows = await self.repository.list_project_activity(project_id, context.tenant_id, limit)
        return [self._activity_from_row(row, ActivityListItem) for row in rows]

    async def create_activity(
        self,
        project_id: UUID,
        payload: ActivityCreate,
        context: RequestContext,
        idempotency_key: str | None,
    ) -> ActivityResponse:
        await self._ensure_project_member(project_id, context)

        # Preserve the existing API behavior: the body client_event_id wins, and
        # Idempotency-Key is used as a fallback logical event id.
        stored_client_event_id = payload.client_event_id or idempotency_key

        row = await self.repository.upsert_activity(project_id, context, payload, stored_client_event_id)

        # Side effects are part of the same database transaction as the durable
        # activity insert. They run only for the request that actually created the
        # logical event. Retries that hit the unique idempotency key return the
        # existing activity row without incrementing counters again.
        if row["was_inserted"]:
            await self.repository.increment_unread_for_project_members(project_id, context.actor_user_id)
            await self.repository.increment_project_total(project_id)

        await self.session.commit()
        return self._activity_from_row(row, ActivityResponse)

    async def get_unread(self, project_id: UUID, context: RequestContext) -> list[MemberUnread]:
        await self._ensure_project_member(project_id, context)
        rows = await self.repository.get_unread(project_id)
        return [MemberUnread(user_id=row["user_id"], display_name=row["display_name"], unread_count=row["unread_count"]) for row in rows]

    async def _ensure_project_member(self, project_id: UUID, context: RequestContext) -> None:
        member = await self.repository.get_project_member(project_id, context.tenant_id, context.actor_user_id)
        if member is None:
            raise AppError(status_code=403, code="project_access_denied", message="Actor cannot access this project")

    def _activity_from_row(self, row, model_type):
        return model_type(
            id=row["id"],
            project_id=row["project_id"],
            event_type=row["event_type"],
            message=row["message"],
            client_event_id=row["client_event_id"],
            metadata=row["metadata"],
            actor=ActorSummary(id=row["actor_user_id"], display_name=row["actor_display_name"]),
            created_at=row["created_at"],
        )
