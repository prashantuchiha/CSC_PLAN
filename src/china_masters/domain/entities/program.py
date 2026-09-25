from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import DegreeLevel
from china_masters.domain.exceptions import ValidationError


@dataclass(frozen=True, kw_only=True)
class Program(Entity):
    university_id: UUID
    name: str
    degree_level: DegreeLevel = DegreeLevel.MASTERS
    department: str | None = None
    language: str | None = None
    duration_years: Decimal | None = None
    tuition_cny: Decimal | None = None
    application_deadline: date | None = None
    csc_supported: bool | None = None
    notes: str | None = None
    last_verified_at: datetime | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.duration_years is not None and (
            not self.duration_years.is_finite() or self.duration_years <= 0
        ):
            raise ValidationError("Duration must be finite and positive")
        if self.tuition_cny is not None and (
            not self.tuition_cny.is_finite() or self.tuition_cny < 0
        ):
            raise ValidationError("Tuition must be finite and nonnegative")
