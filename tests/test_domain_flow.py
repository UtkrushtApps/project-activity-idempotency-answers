from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db import SessionLocal
from app.main import app

TENANT_ID = "00000000-0000-0000-0000-000000000001"
ACTOR_ID = "00000000-0000-0000-0000-000000000101"
OTHER_MEMBER_ID = "00000000-0000-0000-0000-000000000102"
PROJECT_ID = "11111111-1111-1111-1111-111111111111"
HEADERS = {"X-Tenant-Id": TENANT_ID, "X-Actor-User-Id": ACTOR_ID}


async def _activity_count(client_event_id: str) -> int:
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT count(*) FROM activities WHERE client_event_id = :client_event_id"), {"client_event_id": client_event_id})
        return int(result.scalar_one())


async def _member_unread() -> int:
    async with SessionLocal() as session:
        result = await session.execute(
            text(
                """
                SELECT unread_count
                FROM project_members
                WHERE project_id = CAST(:project_id AS uuid)
                  AND user_id = CAST(:user_id AS uuid)
                """
            ),
            {"project_id": PROJECT_ID, "user_id": OTHER_MEMBER_ID},
        )
        return int(result.scalar_one())


@pytest.mark.asyncio
async def test_activity_creation_preserves_response_shape():
    event_id = f"shape-{uuid4()}"
    payload = {"event_type": "comment.created", "message": "Response shape check", "client_event_id": event_id, "metadata": {"source": "pytest"}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v1/projects/{PROJECT_ID}/activity-events", json=payload, headers=HEADERS)
    assert response.status_code == 201
    body = response.json()
    assert {"id", "project_id", "event_type", "message", "client_event_id", "metadata", "actor", "created_at"}.issubset(body.keys())
    assert body["actor"]["display_name"] == "Maya Rao"


@pytest.mark.asyncio
async def test_retried_activity_does_not_duplicate_rows_or_unread_side_effects():
    event_id = f"retry-{uuid4()}"
    payload = {"event_type": "comment.created", "message": "Retry-safe comment", "client_event_id": event_id, "metadata": {"source": "pytest", "retry": True}}
    headers = {**HEADERS, "Idempotency-Key": event_id}
    before_unread = await _member_unread()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(f"/api/v1/projects/{PROJECT_ID}/activity-events", json=payload, headers=headers)
        second = await client.post(f"/api/v1/projects/{PROJECT_ID}/activity-events", json=payload, headers=headers)
    assert first.status_code in (200, 201)
    assert second.status_code in (200, 201)
    assert first.json()["client_event_id"] == event_id
    assert second.json()["client_event_id"] == event_id
    assert await _activity_count(event_id) == 1
    assert await _member_unread() == before_unread + 1
