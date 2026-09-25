from dataclasses import dataclass

from china_masters.domain.exceptions import ValidationError


@dataclass(frozen=True)
class Page:
    limit: int = 100
    offset: int = 0

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 500 or self.offset < 0:
            raise ValidationError("limit must be 1..500 and offset must be nonnegative")
