import json
from datetime import UTC, datetime

from china_masters.domain.exceptions import ValidationError

type JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def validate_json(value: JSONValue) -> None:
    """Reject NaN, infinity, cycles, and non-JSON values before persistence."""
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValidationError("Value must be finite, JSON-serializable data") from exc

    def check(item: JSONValue) -> None:
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValidationError("JSON object keys must be strings")
            for child in item.values():
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
        elif item is not None and not isinstance(item, (bool, int, float, str)):
            raise ValidationError("Value contains a non-JSON type")

    check(value)
