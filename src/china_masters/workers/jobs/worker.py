"""Single-process polling loop. No SQLAlchemy, API, or provider-specific code."""

import logging
from threading import Event
from uuid import uuid4

from china_masters.application.dto.job_execution import JobExecutionContext
from china_masters.application.services.job_execution import ClaimedJob, JobExecutionService
from china_masters.application.services.job_handlers import JobHandlerRegistry, UnsupportedJobError
from china_masters.domain.entities import ResearchJob
from china_masters.domain.enums import JobStatus
from china_masters.domain.exceptions import ConflictError, ValidationError

logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(
        self,
        execution: JobExecutionService,
        handlers: JobHandlerRegistry,
        *,
        worker_id: str | None = None,
    ) -> None:
        self.execution = execution
        self.handlers = handlers
        self.worker_id = worker_id or f"local-{uuid4().hex}"

    def once(self) -> ResearchJob | None:
        for recovered in self.execution.recover_expired():
            logger.warning(
                "lease recovered job_id=%s job_type=%s status=%s",
                recovered.id,
                recovered.job_type,
                recovered.status,
            )
        claim = self.execution.claim_next(self.worker_id)
        if claim is None:
            return None
        job = claim.job
        logger.info(
            "job claimed job_id=%s job_type=%s worker_id=%s attempts=%s",
            job.id,
            job.job_type,
            self.worker_id,
            job.attempts,
        )
        try:
            handler = self.handlers.get(job.job_type)
        except UnsupportedJobError as exc:
            logger.warning("job unsupported job_id=%s job_type=%s", job.id, job.job_type)
            return self._fail(claim, str(exc), permanent=True)
        try:
            logger.info("job started job_id=%s job_type=%s", job.id, job.job_type)
            result = handler.execute(
                JobExecutionContext(heartbeat=lambda: self.execution.renew(claim)),
                job,
            )
        except Exception as exc:
            logger.exception("job handler failed job_id=%s job_type=%s", job.id, job.job_type)
            return self._fail(claim, f"{type(exc).__name__}: {exc}")
        try:
            updated = self.execution.complete(claim, result)
        except ConflictError:
            logger.warning(
                "job claim lost before completion job_id=%s job_type=%s", job.id, job.job_type
            )
            return None
        except (TypeError, AttributeError, ValidationError) as exc:
            logger.exception(
                "job handler returned invalid result job_id=%s job_type=%s", job.id, job.job_type
            )
            return self._fail(claim, f"{type(exc).__name__}: {exc}")
        logger.info(
            "job completed job_id=%s job_type=%s status=%s", job.id, job.job_type, updated.status
        )
        return updated

    def _fail(
        self, claim: ClaimedJob, message: str, *, permanent: bool = False
    ) -> ResearchJob | None:
        try:
            updated = self.execution.fail(claim, message, permanent=permanent)
        except ConflictError:
            logger.warning(
                "job claim lost before failure update job_id=%s job_type=%s",
                claim.job.id,
                claim.job.job_type,
            )
            return None
        label = (
            "job failed permanently"
            if updated.status == JobStatus.FAILED
            else "job scheduled for retry"
        )
        logger.warning(
            "%s job_id=%s job_type=%s attempts=%s next_attempt_at=%s",
            label,
            updated.id,
            updated.job_type,
            updated.attempts,
            updated.next_attempt_at,
        )
        return updated

    def run(self, stop: Event) -> None:
        while not stop.is_set():
            processed = self.once()
            if processed is None:
                stop.wait(self.execution.policy.poll_interval_seconds)
