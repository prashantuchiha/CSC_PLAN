"""Small typed schemas for the three Phase 2 handlers; unknown legacy keys survive."""

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from china_masters.domain.enums import JobType
from china_masters.domain.exceptions import ValidationError
from china_masters.domain.value_objects import JSONValue, validate_json


@dataclass(frozen=True)
class ProfessorResearchPayload:
    focus: str | None = None
    filters: tuple[str, ...] = ()
    review_required: bool = False
    review_approved: bool = False
    fail_until_attempt: int = 0


@dataclass(frozen=True)
class UniversityResearchPayload:
    focus: str | None = None
    review_required: bool = False
    review_approved: bool = False
    fail_until_attempt: int = 0


@dataclass(frozen=True)
class GeneralCSCResearchPayload:
    topic: str | None = None
    review_required: bool = False
    review_approved: bool = False
    fail_until_attempt: int = 0


def _common(payload: dict[str, JSONValue]) -> tuple[bool, bool, int]:
    review = payload.get("review_required", False)
    approved = payload.get("review_approved", False)
    failure = payload.get("fail_until_attempt", 0)
    if not isinstance(review, bool):
        raise ValidationError("review_required must be a boolean")
    if not isinstance(approved, bool):
        raise ValidationError("review_approved must be a boolean")
    if type(failure) is not int or not 0 <= failure <= 100:
        raise ValidationError("fail_until_attempt must be an integer from 0 to 100")
    return review, approved, failure


def _optional_text(payload: dict[str, JSONValue], key: str) -> str | None:
    value = payload.get(key)
    if value is not None and (not isinstance(value, str) or not value.strip()):
        raise ValidationError(f"{key} must be a nonempty string")
    return value


def professor_payload(payload: dict[str, JSONValue]) -> ProfessorResearchPayload:
    review, approved, failure = _common(payload)
    filters = payload.get("filters", [])
    if not isinstance(filters, list) or not all(
        isinstance(item, str) and item.strip() for item in filters
    ):
        raise ValidationError("filters must be a list of nonempty strings")
    return ProfessorResearchPayload(
        focus=_optional_text(payload, "focus"),
        filters=tuple(str(item) for item in filters),
        review_required=review,
        review_approved=approved,
        fail_until_attempt=failure,
    )


def university_payload(payload: dict[str, JSONValue]) -> UniversityResearchPayload:
    review, approved, failure = _common(payload)
    return UniversityResearchPayload(
        focus=_optional_text(payload, "focus"),
        review_required=review,
        review_approved=approved,
        fail_until_attempt=failure,
    )


def general_payload(payload: dict[str, JSONValue]) -> GeneralCSCResearchPayload:
    review, approved, failure = _common(payload)
    return GeneralCSCResearchPayload(
        topic=_optional_text(payload, "topic"),
        review_required=review,
        review_approved=approved,
        fail_until_attempt=failure,
    )


type PayloadValidator = Callable[[dict[str, JSONValue]], object]


class JobPayloadRegistry:
    def __init__(self, validators: dict[JobType, PayloadValidator] | None = None) -> None:
        self._validators = validators or {}

    def normalize(self, job_type: JobType, payload: dict[str, JSONValue]) -> dict[str, JSONValue]:
        validate_json(payload)
        validator = self._validators.get(job_type)
        if validator is not None:
            validator(payload)
        return deepcopy(payload)


def phase2_payload_registry() -> JobPayloadRegistry:
    return JobPayloadRegistry(
        {
            JobType.PROFESSOR_RESEARCH: professor_payload,
            JobType.UNIVERSITY_RESEARCH: university_payload,
            JobType.GENERAL_CSC_RESEARCH: general_payload,
        }
    )
