from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from china_masters.domain.entities import (
    ProfessorContact,
    Program,
    ResearchJob,
    StudyPlan,
    University,
)
from china_masters.domain.enums import ContactType, JobType
from china_masters.domain.exceptions import ValidationError
from china_masters.domain.value_objects import validate_json


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "non-string key"}, ("tuple",)])
def test_non_json_values_rejected(value):
    with pytest.raises(ValidationError):
        validate_json(value)


def test_timestamps_are_normalized_to_utc():
    time = datetime(2026, 1, 1, 12, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    university = University(canonical_name="Example", created_at=time)
    assert university.created_at == time.astimezone(UTC)
    assert university.created_at.tzinfo == UTC


def test_entity_invariants():
    with pytest.raises(ValidationError):
        Program(university_id=uuid4(), name="Invalid", duration_years=Decimal("-1"))
    with pytest.raises(ValidationError):
        StudyPlan(version=0)
    with pytest.raises(ValidationError):
        ProfessorContact(
            professor_id=uuid4(),
            contact_type=ContactType.EMAIL,
            value="demo@example.invalid",
            verified=True,
        )
    with pytest.raises(ValidationError):
        ResearchJob(job_type=JobType.INBOX_SYNC, entity_id=uuid4())
