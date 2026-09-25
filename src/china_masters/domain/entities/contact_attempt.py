from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    ContactType,
)
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class ContactAttempt(Entity):
    professor_id: UUID
    channel: ContactType
    outcome: str
    email_record_id: UUID | None = None
    attempted_at: datetime = field(default_factory=utc_now)
    notes: str | None = None
