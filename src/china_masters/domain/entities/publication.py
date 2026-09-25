from dataclasses import dataclass
from uuid import UUID

from china_masters.domain.entities.base import Entity


@dataclass(frozen=True, kw_only=True)
class Publication(Entity):
    professor_id: UUID
    title: str
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    abstract: str | None = None
    source_id: UUID | None = None
