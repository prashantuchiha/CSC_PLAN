from dataclasses import dataclass, field
from datetime import datetime

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    SourceType,
)
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True, kw_only=True)
class Source(Entity):
    url: str
    source_type: SourceType
    normalized_url: str | None = None
    title: str | None = None
    publisher: str | None = None
    domain: str | None = None
    retrieved_at: datetime = field(default_factory=utc_now)
    published_at: datetime | None = None
    content_hash: str | None = None
    local_snapshot_path: str | None = None
    notes: str | None = None
