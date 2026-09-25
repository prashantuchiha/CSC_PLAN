from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from uuid import UUID, uuid4

from china_masters.domain.exceptions import ValidationError


@dataclass(frozen=True, kw_only=True)
class Entity:
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if isinstance(value, datetime) and value.utcoffset() is None:
                raise ValidationError(f"{item.name} must include a timezone")
            if isinstance(value, datetime):
                object.__setattr__(self, item.name, value.astimezone(UTC))
            if isinstance(value, str) and not value.strip():
                raise ValidationError(f"{item.name} must not be blank; use None for absent values")
