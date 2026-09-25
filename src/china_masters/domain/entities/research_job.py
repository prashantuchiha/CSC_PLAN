from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import (
    EntityType,
    JobStatus,
    JobType,
)
from china_masters.domain.exceptions import ValidationError
from china_masters.domain.value_objects import JSONValue, utc_now, validate_json


@dataclass(frozen=True, kw_only=True)
class ResearchJob(Entity):
    job_type: JobType
    status: JobStatus = JobStatus.QUEUED
    priority: int = 0
    entity_type: EntityType | None = None
    entity_id: UUID | None = None
    payload_json: dict[str, JSONValue] = field(default_factory=dict)
    result_json: dict[str, JSONValue] | None = None
    error_message: str | None = None
    attempts: int = 0
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    worker_id: str | None = None
    claim_token: UUID | None = None
    lease_expires_at: datetime | None = None
    next_attempt_at: datetime | None = None
    revision: int = 0

    def __post_init__(self) -> None:
        super().__post_init__()
        if not 0 <= self.priority <= 100 or self.attempts < 0 or self.revision < 0:
            raise ValidationError("Invalid priority, attempt count, or revision")
        if (self.entity_id is None) != (self.entity_type is None):
            raise ValidationError("Entity type and ID must be supplied together")
        if (self.worker_id is None) != (self.claim_token is None):
            raise ValidationError("Worker and claim token must be supplied together")
        if self.lease_expires_at is not None and self.worker_id is None:
            raise ValidationError("A lease requires an owner")
        validate_json(self.payload_json)
        validate_json(self.result_json)

    def transition(
        self,
        target: JobStatus,
        *,
        result: dict[str, JSONValue] | None = None,
        error: str | None = None,
    ) -> "ResearchJob":
        from dataclasses import replace

        from china_masters.domain.exceptions import ValidationError

        allowed = {
            JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.CANCELLED},
            JobStatus.RUNNING: {
                JobStatus.WAITING_FOR_REVIEW,
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            },
            JobStatus.WAITING_FOR_REVIEW: {JobStatus.QUEUED, JobStatus.CANCELLED},
            JobStatus.FAILED: {JobStatus.QUEUED, JobStatus.CANCELLED},
            JobStatus.COMPLETED: set(),
            JobStatus.CANCELLED: set(),
        }
        if target not in allowed[self.status]:
            raise ValidationError(f"Cannot transition {self.status} to {target}")
        if target == JobStatus.FAILED and (not error or not error.strip()):
            raise ValidationError("Failed jobs require an error message")
        if result is not None and target not in {JobStatus.COMPLETED, JobStatus.WAITING_FOR_REVIEW}:
            raise ValidationError("Results require completion or review")
        if error is not None and target != JobStatus.FAILED:
            raise ValidationError("Errors require FAILED status")
        now = utc_now()
        terminal = target in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}
        return replace(
            self,
            status=target,
            revision=self.revision + 1,
            attempts=self.attempts + (target == JobStatus.RUNNING),
            started_at=now
            if target == JobStatus.RUNNING
            else (None if target == JobStatus.QUEUED else self.started_at),
            completed_at=now if terminal else None,
            result_json=result,
            error_message=error,
            worker_id=self.worker_id if target == JobStatus.RUNNING else None,
            claim_token=self.claim_token if target == JobStatus.RUNNING else None,
            lease_expires_at=self.lease_expires_at if target == JobStatus.RUNNING else None,
            next_attempt_at=None,
        )
