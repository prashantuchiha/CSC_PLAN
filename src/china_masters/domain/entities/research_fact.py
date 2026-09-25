from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import EntityType, VerificationStatus
from china_masters.domain.value_objects import JSONValue, validate_json


@dataclass(frozen=True, kw_only=True)
class ResearchFact(Entity):
    entity_type: EntityType
    entity_id: UUID
    field_name: str
    value: JSONValue
    source_id: UUID
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_at: datetime | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        validate_json(self.value)
