from collections.abc import Callable
from dataclasses import dataclass, field

from china_masters.domain.value_objects import JSONValue, validate_json


@dataclass(frozen=True)
class JobExecutionResult:
    data: dict[str, JSONValue] = field(default_factory=dict)
    review_required: bool = False
    message: str | None = None

    def __post_init__(self) -> None:
        validate_json(self.data)


@dataclass(frozen=True)
class JobExecutionContext:
    """Handlers may call heartbeat during long work without seeing persistence details."""

    heartbeat: Callable[[], None]
