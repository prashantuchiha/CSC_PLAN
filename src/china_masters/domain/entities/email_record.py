from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    EmailStatus,
)
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class EmailRecord(Entity):
    professor_id: UUID
    provider: str
    subject: str
    provider_message_id: str | None = None
    provider_thread_id: str | None = None
    status: EmailStatus = EmailStatus.DRAFT
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    received_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
