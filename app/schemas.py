from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ActorSummary(BaseModel):
    id: UUID
    display_name: str


class ActivityCreate(BaseModel):
    event_type: str = Field(min_length=3, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    client_event_id: str | None = Field(default=None, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActivityResponse(BaseModel):
    id: int
    project_id: UUID
    event_type: str
    message: str
    client_event_id: str | None
    metadata: dict[str, Any]
    actor: ActorSummary
    created_at: datetime


class ActivityListItem(ActivityResponse):
    pass


class MemberUnread(BaseModel):
    user_id: UUID
    display_name: str
    unread_count: int
