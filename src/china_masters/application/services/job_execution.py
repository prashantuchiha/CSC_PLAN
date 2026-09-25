"""Claim lifecycle and retry policy, independent of a database or transport."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from china_masters.application.dto.job_execution import JobExecutionResult
from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.domain.entities import ResearchJob
from china_masters.domain.enums import JobStatus
from china_masters.domain.exceptions import ConflictError, NotFoundError, ValidationError
from china_masters.domain.value_objects import utc_now


@dataclass(frozen=True)
class JobPolicy:
    max_attempts: int = 3
    lease_seconds: int = 300
    poll_interval_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1 or self.lease_seconds < 1 or self.poll_interval_seconds <= 0:
            raise ValidationError("Job policy values must be positive")

    def backoff(self, attempts: int) -> timedelta:
        return timedelta(seconds=min(60, 2 ** min(attempts - 1, 6)))


@dataclass(frozen=True)
class ClaimedJob:
    job: ResearchJob
    token: UUID
    worker_id: str


class JobExecutionService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        policy: JobPolicy,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._uow = uow_factory
        self.policy = policy
        self._clock = clock

    def claim_next(self, worker_id: str) -> ClaimedJob | None:
        if not worker_id.strip() or len(worker_id) > 128:
            raise ValidationError("Worker ID must contain 1..128 characters")
        now = self._clock()
        token = uuid4()
        with self._uow() as uow:
            job = uow.research_jobs.claim_next(
                worker_id=worker_id,
                claim_token=token,
                now=now,
                lease_expires_at=now + timedelta(seconds=self.policy.lease_seconds),
                max_attempts=self.policy.max_attempts,
            )
            if job is not None:
                uow.commit()
        return ClaimedJob(job, token, worker_id) if job is not None else None

    def _owned(self, job: ResearchJob | None, claim: ClaimedJob, now: datetime) -> ResearchJob:
        if job is None:
            raise NotFoundError(f"Job {claim.job.id} does not exist")
        if (
            job.status != JobStatus.RUNNING
            or job.worker_id != claim.worker_id
            or job.claim_token != claim.token
            or job.lease_expires_at is None
            or job.lease_expires_at <= now
        ):
            raise ConflictError("Job claim is no longer active")
        return job

    def complete(self, claim: ClaimedJob, result: JobExecutionResult) -> ResearchJob:
        now = self._clock()
        with self._uow() as uow:
            job = self._owned(uow.research_jobs.get(claim.job.id), claim, now)
            data = dict(result.data)
            if result.message is not None:
                data["message"] = result.message
            status = JobStatus.WAITING_FOR_REVIEW if result.review_required else JobStatus.COMPLETED
            updated = job.transition(status, result=data)
            uow.research_jobs.save(updated)
            uow.commit()
        return updated

    def renew(self, claim: ClaimedJob) -> None:
        now = self._clock()
        with self._uow() as uow:
            job = self._owned(uow.research_jobs.get(claim.job.id), claim, now)
            updated = replace(
                job,
                lease_expires_at=now + timedelta(seconds=self.policy.lease_seconds),
                revision=job.revision + 1,
            )
            uow.research_jobs.save(updated)
            uow.commit()

    def fail(self, claim: ClaimedJob, error: str, *, permanent: bool = False) -> ResearchJob:
        now = self._clock()
        message = (error.strip() or "Unknown handler failure")[:500]
        with self._uow() as uow:
            job = self._owned(uow.research_jobs.get(claim.job.id), claim, now)
            exhausted = permanent or job.attempts >= self.policy.max_attempts
            if exhausted:
                updated = job.transition(JobStatus.FAILED, error=message)
            else:
                updated = replace(
                    job,
                    status=JobStatus.QUEUED,
                    revision=job.revision + 1,
                    worker_id=None,
                    claim_token=None,
                    lease_expires_at=None,
                    next_attempt_at=now + self.policy.backoff(job.attempts),
                    started_at=None,
                    completed_at=None,
                    result_json=None,
                    error_message=message,
                )
            uow.research_jobs.save(updated)
            uow.commit()
        return updated

    def recover_expired(self, *, limit: int = 100) -> list[ResearchJob]:
        now = self._clock()
        recovered: list[ResearchJob] = []
        with self._uow() as uow:
            for job in uow.research_jobs.expired(now, limit=limit):
                message = f"Lease expired for worker {job.worker_id}"[:500]
                if job.attempts >= self.policy.max_attempts:
                    updated = job.transition(JobStatus.FAILED, error=message)
                else:
                    updated = replace(
                        job,
                        status=JobStatus.QUEUED,
                        revision=job.revision + 1,
                        worker_id=None,
                        claim_token=None,
                        lease_expires_at=None,
                        next_attempt_at=now + self.policy.backoff(job.attempts),
                        started_at=None,
                        completed_at=None,
                        result_json=None,
                        error_message=message,
                    )
                try:
                    uow.research_jobs.save(updated)
                except ConflictError:
                    continue
                recovered.append(updated)
            for job in uow.research_jobs.exhausted_queued(self.policy.max_attempts, limit=limit):
                updated = replace(
                    job,
                    status=JobStatus.FAILED,
                    revision=job.revision + 1,
                    completed_at=now,
                    next_attempt_at=None,
                    error_message="Attempt budget exhausted under current worker settings",
                )
                try:
                    uow.research_jobs.save(updated)
                except ConflictError:
                    continue
                recovered.append(updated)
            if recovered:
                uow.commit()
        return recovered
