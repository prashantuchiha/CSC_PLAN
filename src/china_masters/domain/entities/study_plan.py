from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    StudyPlanStatus,
)
from china_masters.domain.exceptions import ValidationError
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class StudyPlan(Entity):
    professor_id: UUID | None = None
    university_id: UUID | None = None
    version: int = 1
    status: StudyPlanStatus = StudyPlanStatus.DRAFT
    file_path: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.version < 1:
            raise ValidationError("Study-plan version must be positive")
