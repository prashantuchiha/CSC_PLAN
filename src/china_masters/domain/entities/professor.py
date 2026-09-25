from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    ProfessorStatus,
)
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class Professor(Entity):
    university_id: UUID
    name_en: str
    department: str | None = None
    name_zh: str | None = None
    title: str | None = None
    official_profile_url: str | None = None
    research_summary: str | None = None
    status: ProfessorStatus = ProfessorStatus.NEW
    last_verified_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
