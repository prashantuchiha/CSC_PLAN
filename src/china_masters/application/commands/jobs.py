from dataclasses import dataclass, field
from uuid import UUID

from china_masters.domain.enums import EntityType, JobType
from china_masters.domain.value_objects import JSONValue


@dataclass(frozen=True, kw_only=True)
class CreateJobs:
    job_type: JobType
    entity_type: EntityType | None = None
    entity_ids: tuple[UUID, ...] = ()
    priority: int = 0
    payload: dict[str, JSONValue] = field(default_factory=dict)
