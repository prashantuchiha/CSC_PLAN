from dataclasses import dataclass
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import ContactType
from china_masters.domain.exceptions import ValidationError


@dataclass(frozen=True, kw_only=True)
class ProfessorContact(Entity):
    professor_id: UUID
    contact_type: ContactType
    value: str
    source_id: UUID | None = None
    verified: bool = False
    notes: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.verified and self.source_id is None:
            raise ValidationError("Verified contact methods require a source")
