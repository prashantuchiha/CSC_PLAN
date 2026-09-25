from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from uuid import UUID, uuid4

from china_masters.application.commands.jobs import CreateJobs
from china_masters.application.dto.job_payloads import JobPayloadRegistry, phase2_payload_registry
from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.application.queries.pagination import Page
from china_masters.application.services.job_execution import JobPolicy
from china_masters.application.services.references import require_reference
from china_masters.domain.entities import ResearchJob
from china_masters.domain.enums import EntityType, JobStatus, JobType
from china_masters.domain.exceptions import ConflictError, NotFoundError, ValidationError
from china_masters.domain.value_objects import JSONValue, utc_now

TARGETS = {
    JobType.UNIVERSITY_RESEARCH: EntityType.UNIVERSITY,
    JobType.PROGRAM_RESEARCH: EntityType.PROGRAM,
    JobType.PROFESSOR_DISCOVERY: EntityType.UNIVERSITY,
    JobType.PROFESSOR_RESEARCH: EntityType.PROFESSOR,
    JobType.PROFESSOR_PUBLICATION_RESEARCH: EntityType.PROFESSOR,
    JobType.STUDY_PLAN_GENERATION: EntityType.PROFESSOR,
    JobType.EMAIL_DRAFT: EntityType.PROFESSOR,
    JobType.EMAIL_SEND: EntityType.EMAIL_RECORD,
}


class JobService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        payloads: JobPayloadRegistry | None = None,
        policy: JobPolicy | None = None,
    ) -> None:
        self._uow = uow_factory
        self._payloads = payloads or phase2_payload_registry()
        self._policy = policy or JobPolicy()

    def create(self, command: CreateJobs) -> list[ResearchJob]:
        expected = TARGETS.get(command.job_type)
        kind = command.entity_type or expected
        ids = command.entity_ids
        if len(ids) > 500 or len(ids) != len(set(ids)):
            raise ValidationError("Batch must contain at most 500 distinct entity IDs")
        if not 0 <= command.priority <= 100:
            raise ValidationError("Priority must be 0..100")
        if expected is not None and (kind != expected or not ids):
            raise ValidationError(f"{command.job_type} requires {expected} entity IDs")
        if expected is None and (kind is not None or ids):
            raise ValidationError(f"{command.job_type} is a global job and takes no entity IDs")
        payload = self._payloads.normalize(command.job_type, command.payload)
        with self._uow() as uow:
            if kind is not None:
                for entity_id in ids:
                    require_reference(uow, kind, entity_id)
            jobs = [
                ResearchJob(
                    job_type=command.job_type,
                    priority=command.priority,
                    entity_type=kind,
                    entity_id=entity_id,
                    payload_json=deepcopy(payload),
                )
                for entity_id in (ids or (None,))
            ]
            for job in jobs:
                uow.research_jobs.add(job)
            uow.commit()
        return jobs

    def get(self, job_id: UUID) -> ResearchJob:
        with self._uow() as uow:
            job = uow.research_jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} does not exist")
            return job

    def list(self, page: Page = Page(), *, status: JobStatus | None = None) -> list[ResearchJob]:
        with self._uow() as uow:
            if status is not None:
                return uow.research_jobs.by_status(status, limit=page.limit, offset=page.offset)
            return uow.research_jobs.list(limit=page.limit, offset=page.offset)

    def transition(
        self,
        job_id: UUID,
        status: JobStatus,
        *,
        result: dict[str, JSONValue] | None = None,
        error: str | None = None,
    ) -> ResearchJob:
        with self._uow() as uow:
            job = uow.research_jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} does not exist")
            if status == JobStatus.CANCELLED and job.status == status:
                return job
            if job.status == JobStatus.RUNNING and status != JobStatus.CANCELLED:
                if job.worker_id != "manual":
                    raise ValidationError("Worker-owned jobs are completed by their worker")
                if job.lease_expires_at is None or job.lease_expires_at <= utc_now():
                    raise ConflictError("Manual job lease has expired")
            updated = job.transition(status, result=result, error=error)
            if status == JobStatus.RUNNING:
                updated = replace(
                    updated,
                    worker_id="manual",
                    claim_token=uuid4(),
                    lease_expires_at=utc_now() + timedelta(seconds=self._policy.lease_seconds),
                )
            if status == JobStatus.QUEUED and updated.attempts >= self._policy.max_attempts:
                raise ValidationError("Attempt budget exhausted; create a new job")
            uow.research_jobs.save(updated)
            uow.commit()
        return updated

    def cancel(self, job_id: UUID) -> ResearchJob:
        return self.transition(job_id, JobStatus.CANCELLED)

    def resume(self, job_id: UUID) -> ResearchJob:
        with self._uow() as uow:
            job = uow.research_jobs.get(job_id)
            if job is None:
                raise NotFoundError(f"Job {job_id} does not exist")
            if job.status != JobStatus.WAITING_FOR_REVIEW:
                raise ValidationError("Only a review-gated job can be resumed")
            if job.attempts >= self._policy.max_attempts:
                raise ValidationError("Attempt budget exhausted; create a new job")
            updated = replace(
                job.transition(JobStatus.QUEUED),
                payload_json={**job.payload_json, "review_approved": True},
            )
            uow.research_jobs.save(updated)
            uow.commit()
        return updated
