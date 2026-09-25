from dataclasses import dataclass, field
from datetime import datetime

from china_masters.domain.entities.base import Entity
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class University(Entity):
    canonical_name: str
    chinese_name: str | None = None
    abbreviation: str | None = None
    city: str | None = None
    province: str | None = None
    official_website: str | None = None
    international_admissions_url: str | None = None
    notes: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
