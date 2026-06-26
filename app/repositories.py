import json
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import RequestContext
from app.schemas import ActivityCreate


class ActivityRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_project_member(self, project_id: UUID, tenant_id: UUID, actor_user_id: UUID):
        result = await self.session.execute(
            text(
                """
                SELECT pm.project_id, pm.user_id, pm.role
                FROM project_members pm
                JOIN projects p ON p.id = pm.project_id
                JOIN users u ON u.id = pm.user_id
                WHERE pm.project_id = CAST(:project_id AS uuid)
                  AND p.tenant_id = CAST(:tenant_id AS uuid)
                  AND pm.user_id = CAST(:actor_user_id AS uuid)
                  AND u.is_active = true
                """
            ),
            {"project_id": str(project_id), "tenant_id": str(tenant_id), "actor_user_id": str(actor_user_id)},
        )
        return result.mappings().first()

    async def upsert_activity(self, project_id: UUID, context: RequestContext, payload: ActivityCreate, client_event_id: str | None):
        result = await self.session.execute(
            text(
                """
                WITH upserted AS (
                    INSERT INTO activities (tenant_id, project_id, actor_user_id, event_type, message, client_event_id, metadata)
                    VALUES (
                        CAST(:tenant_id AS uuid),
                        CAST(:project_id AS uuid),
                        CAST(:actor_user_id AS uuid),
                        :event_type,
                        :message,
                        :client_event_id,
                        CAST(:metadata_json AS jsonb)
                    )
                    ON CONFLICT (tenant_id, project_id, actor_user_id, client_event_id)
                    WHERE client_event_id IS NOT NULL
                    DO UPDATE SET client_event_id = activities.client_event_id
                    RETURNING
                        id,
                        tenant_id,
                        project_id,
                        actor_user_id,
                        event_type,
                        message,
                        client_event_id,
                        metadata,
                        created_at,
                        (xmax = 0) AS was_inserted
                )
                SELECT upserted.*, u.display_name AS actor_display_name
                FROM upserted
                JOIN users u ON u.id = upserted.actor_user_id
                """
            ),
            {
                "tenant_id": str(context.tenant_id),
                "project_id": str(project_id),
                "actor_user_id": str(context.actor_user_id),
                "event_type": payload.event_type,
                "message": payload.message,
                "client_event_id": client_event_id,
                "metadata_json": json.dumps(payload.metadata),
            },
        )
        return result.mappings().one()

    async def increment_unread_for_project_members(self, project_id: UUID, actor_user_id: UUID) -> None:
        await self.session.execute(
            text(
                """
                UPDATE project_members
                SET unread_count = unread_count + 1
                WHERE project_id = CAST(:project_id AS uuid)
                  AND user_id <> CAST(:actor_user_id AS uuid)
                """
            ),
            {"project_id": str(project_id), "actor_user_id": str(actor_user_id)},
        )

    async def increment_project_total(self, project_id: UUID) -> None:
        await self.session.execute(
            text(
                """
                UPDATE project_activity_totals
                SET total_events = total_events + 1,
                    updated_at = now()
                WHERE project_id = CAST(:project_id AS uuid)
                """
            ),
            {"project_id": str(project_id)},
        )

    async def list_project_activity(self, project_id: UUID, tenant_id: UUID, limit: int):
        result = await self.session.execute(
            text(
                """
                SELECT a.id, a.project_id, a.actor_user_id, a.event_type, a.message, a.client_event_id,
                       a.metadata, a.created_at, u.display_name AS actor_display_name
                FROM activities a
                JOIN users u ON u.id = a.actor_user_id
                WHERE a.project_id = CAST(:project_id AS uuid)
                  AND a.tenant_id = CAST(:tenant_id AS uuid)
                ORDER BY a.created_at DESC, a.id DESC
                LIMIT :limit
                """
            ),
            {"project_id": str(project_id), "tenant_id": str(tenant_id), "limit": limit},
        )
        return result.mappings().all()

    async def get_unread(self, project_id: UUID):
        result = await self.session.execute(
            text(
                """
                SELECT pm.user_id, u.display_name, pm.unread_count
                FROM project_members pm
                JOIN users u ON u.id = pm.user_id
                WHERE pm.project_id = CAST(:project_id AS uuid)
                ORDER BY u.display_name
                """
            ),
            {"project_id": str(project_id)},
        )
        return result.mappings().all()
