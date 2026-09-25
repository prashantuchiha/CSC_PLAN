from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from typer.testing import CliRunner

from china_masters.application.commands.jobs import CreateJobs
from china_masters.application.dto.job_execution import JobExecutionResult
from china_masters.application.dto.job_payloads import phase2_payload_registry
from china_masters.application.services.job_execution import JobExecutionService, JobPolicy
from china_masters.application.services.job_handlers import JobHandlerRegistry
from china_masters.domain.entities import Professor, University
from china_masters.domain.enums import JobStatus, JobType
from china_masters.domain.exceptions import ConflictError, ValidationError
from china_masters.interfaces.cli.main import app
from china_masters.workers.jobs.worker import JobWorker


def make_professor(container, university_name="Fixture University"):
    university = container.universities.create(University(canonical_name=university_name))
    professor = container.professors.create(
        Professor(university_id=university.id, name_en="Synthetic Faculty")
    )
    return university, professor


def controlled_execution(container, *, max_attempts=3, lease_seconds=10):
    current = [datetime(2026, 1, 1, tzinfo=UTC)]
    service = JobExecutionService(
        container.uow,
        JobPolicy(
            max_attempts=max_attempts, lease_seconds=lease_seconds, poll_interval_seconds=0.5
        ),
        clock=lambda: current[0],
    )
    return service, current


def worker_with_clock(container, service):
    original = container.create_worker()
    return JobWorker(service, original.handlers, worker_id="controlled-worker")


def test_claim_is_atomic_and_has_lease(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, _ = controlled_execution(container)
    claim = service.claim_next("worker-a")
    assert claim is not None
    assert claim.job.id == job.id
    assert claim.job.status == JobStatus.RUNNING
    assert claim.job.attempts == 1
    assert claim.job.worker_id == "worker-a"
    assert claim.job.lease_expires_at > claim.job.started_at
    assert claim.token == claim.job.claim_token
    assert service.claim_next("worker-b") is None


def test_concurrent_claimers_get_distinct_ownership(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, _ = controlled_execution(container)
    barrier = Barrier(2)

    def attempt(worker_id):
        barrier.wait(timeout=5)
        return service.claim_next(worker_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(attempt, ("one", "two")))
    assert sum(claim is not None for claim in claims) == 1
    assert next(claim for claim in claims if claim is not None).job.id == job.id


def test_fake_professor_pipeline_persists_result_without_evidence(container):
    _, professor = make_professor(container)
    (job,) = container.jobs.create(
        CreateJobs(
            job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(professor.id,), payload={"demo": True}
        )
    )
    result = container.create_worker().once()
    assert result is not None
    assert result.id == job.id
    assert result.status == JobStatus.COMPLETED
    assert result.attempts == 1
    assert result.worker_id is result.claim_token is result.lease_expires_at is None
    assert result.result_json["synthetic"] is True
    assert result.result_json["candidate_facts"][0]["entity_id"] == str(professor.id)
    assert container.jobs.get(job.id).result_json == result.result_json
    assert container.evidence.list_facts() == []
    assert container.create_worker().once() is None


def test_failures_backoff_then_complete(container):
    _, professor = make_professor(container)
    (job,) = container.jobs.create(
        CreateJobs(
            job_type=JobType.PROFESSOR_RESEARCH,
            entity_ids=(professor.id,),
            payload={"fail_until_attempt": 2},
        )
    )
    service, current = controlled_execution(container)
    worker = worker_with_clock(container, service)
    first = worker.once()
    assert first.status == JobStatus.QUEUED
    assert first.attempts == 1
    assert first.next_attempt_at == current[0] + timedelta(seconds=1)
    assert "Synthetic transient" in first.error_message
    assert worker.once() is None
    current[0] += timedelta(seconds=1)
    second = worker.once()
    assert second.status == JobStatus.QUEUED
    assert second.attempts == 2
    assert second.next_attempt_at == current[0] + timedelta(seconds=2)
    assert worker.once() is None
    current[0] += timedelta(seconds=2)
    completed = worker.once()
    assert completed.status == JobStatus.COMPLETED
    assert completed.attempts == 3
    assert completed.error_message is None
    assert container.jobs.get(job.id) == completed


def test_delayed_retry_does_not_block_other_job(container):
    (high,) = container.jobs.create(
        CreateJobs(
            job_type=JobType.GENERAL_CSC_RESEARCH, priority=100, payload={"fail_until_attempt": 1}
        )
    )
    (low,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH, priority=0))
    service, _ = controlled_execution(container)
    worker = worker_with_clock(container, service)
    first = worker.once()
    assert first.id == high.id and first.status == JobStatus.QUEUED
    second = worker.once()
    assert second.id == low.id and second.status == JobStatus.COMPLETED


def test_failure_exhaustion_and_bounded_error(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, _ = controlled_execution(container, max_attempts=1)

    class HugeFailure:
        job_type = JobType.GENERAL_CSC_RESEARCH

        def execute(self, context, job):
            raise RuntimeError("x" * 2000)

    worker = JobWorker(service, JobHandlerRegistry((HugeFailure(),)))
    result = worker.once()
    assert result.status == JobStatus.FAILED
    assert result.attempts == 1
    assert len(result.error_message) == 500
    assert service.claim_next("other") is None
    assert container.jobs.get(job.id) == result


def test_lowering_attempt_limit_fails_queued_job(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, current = controlled_execution(container, max_attempts=3)
    claim = service.claim_next("worker-a")
    assert service.fail(claim, "temporary").status == JobStatus.QUEUED
    reduced = JobExecutionService(
        container.uow,
        JobPolicy(max_attempts=1, lease_seconds=10),
        clock=lambda: current[0],
    )
    (recovered,) = reduced.recover_expired()
    assert recovered.id == job.id
    assert recovered.status == JobStatus.FAILED
    assert recovered.completed_at == current[0]
    assert reduced.claim_next("worker-b") is None


def test_expired_lease_recovers_and_stale_worker_cannot_finish(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, current = controlled_execution(container, lease_seconds=10)
    old = service.claim_next("worker-a")
    current[0] += timedelta(seconds=9)
    assert service.recover_expired() == []
    assert service.claim_next("worker-b") is None
    service.renew(old)
    current[0] += timedelta(seconds=9)
    assert service.recover_expired() == []
    current[0] += timedelta(seconds=1)
    (recovered,) = service.recover_expired()
    assert recovered.id == job.id
    assert recovered.status == JobStatus.QUEUED
    expected_retry = current[0] + timedelta(seconds=1)
    assert recovered.next_attempt_at == expected_retry
    with pytest.raises(ConflictError):
        service.complete(old, JobExecutionResult(data={"stale": True}))
    assert service.claim_next("worker-b") is None
    current[0] += timedelta(seconds=1)
    fresh = service.claim_next("worker-b")
    assert fresh is not None and fresh.token != old.token
    assert fresh.job.attempts == 2
    assert (
        service.complete(fresh, JobExecutionResult(data={"fresh": True})).status
        == JobStatus.COMPLETED
    )


def test_exhausted_expired_lease_fails(container):
    container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, current = controlled_execution(container, max_attempts=1, lease_seconds=10)
    service.claim_next("worker-a")
    current[0] += timedelta(seconds=10)
    (recovered,) = service.recover_expired()
    assert recovered.status == JobStatus.FAILED
    assert recovered.completed_at is not None
    assert service.claim_next("worker-b") is None


def test_review_gate_and_resume(container):
    (job,) = container.jobs.create(
        CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH, payload={"review_required": True})
    )
    worker = container.create_worker()
    waiting = worker.once()
    assert waiting.status == JobStatus.WAITING_FOR_REVIEW
    assert waiting.result_json["synthetic"] is True
    assert container.jobs.get(job.id) == waiting
    assert worker.once() is None
    resumed = container.jobs.resume(job.id)
    assert resumed.status == JobStatus.QUEUED
    assert resumed.payload_json["review_approved"] is True
    assert resumed.result_json is None
    finished = worker.once()
    assert finished.status == JobStatus.COMPLETED
    assert finished.attempts == 2
    with pytest.raises(ValidationError):
        container.jobs.resume(job.id)


def test_unsupported_job_fails_permanently(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.INBOX_SYNC))
    result = container.create_worker().once()
    assert result.id == job.id
    assert result.status == JobStatus.FAILED
    assert result.attempts == 1
    assert "No handler registered" in result.error_message
    assert container.create_worker().once() is None


def test_invalid_handler_result_is_retried_without_crashing_worker(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, _ = controlled_execution(container)

    class BadResult:
        job_type = JobType.GENERAL_CSC_RESEARCH

        def execute(self, context, job):
            return None

    worker = JobWorker(service, JobHandlerRegistry((BadResult(),)))
    result = worker.once()
    assert result.id == job.id
    assert result.status == JobStatus.QUEUED
    assert result.attempts == 1
    assert "AttributeError" in result.error_message


def test_worker_once_at_most_one_and_cross_university_batch(container):
    _, professor_a = make_professor(container, "A")
    _, professor_b = make_professor(container, "B")
    jobs = container.jobs.create(
        CreateJobs(job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(professor_a.id, professor_b.id))
    )
    worker = container.create_worker()
    first = worker.once()
    assert first.status == JobStatus.COMPLETED
    assert len(container.jobs.list(status=JobStatus.QUEUED)) == 1
    second = worker.once()
    assert second.status == JobStatus.COMPLETED
    assert {first.id, second.id} == {job.id for job in jobs}


def test_idle_worker_waits_instead_of_spinning(container):
    worker = container.create_worker()

    class StopAfterWait:
        waits = 0

        def is_set(self):
            return self.waits > 0

        def wait(self, seconds):
            assert seconds == container.job_policy.poll_interval_seconds
            self.waits += 1

    stop = StopAfterWait()
    worker.run(stop)
    assert stop.waits == 1


def test_typed_payloads_preserve_phase_one_keys(container):
    _, professor = make_professor(container)
    (job,) = container.jobs.create(
        CreateJobs(
            job_type=JobType.PROFESSOR_RESEARCH,
            entity_ids=(professor.id,),
            payload={"demo": True, "filters": ["AI"]},
        )
    )
    assert job.payload_json == {"demo": True, "filters": ["AI"]}
    with pytest.raises(ValidationError):
        container.jobs.create(
            CreateJobs(
                job_type=JobType.PROFESSOR_RESEARCH,
                entity_ids=(professor.id,),
                payload={"filters": "wrong type"},
            )
        )
    with pytest.raises(ValidationError):
        container.jobs.create(
            CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH, payload={"review_required": "yes"})
        )
    assert phase2_payload_registry().normalize(JobType.INBOX_SYNC, {"legacy": 1}) == {"legacy": 1}


def test_cancellation_during_work_rejects_completion(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    service, _ = controlled_execution(container)
    claim = service.claim_next("worker-a")
    assert container.jobs.cancel(job.id).status == JobStatus.CANCELLED
    with pytest.raises(ConflictError):
        service.complete(claim, JobExecutionResult(data={"too late": True}))


def test_cli_worker_once_and_existing_commands(settings, monkeypatch):
    monkeypatch.setenv("CM_DATABASE_URL", settings.database_url)
    monkeypatch.setenv("CM_WORKSPACE_ROOT", str(settings.workspace_root))
    runner = CliRunner()
    assert runner.invoke(app, ["health"]).exit_code == 0
    assert runner.invoke(app, ["university", "list"]).exit_code == 0
    assert runner.invoke(app, ["professor", "list"]).exit_code == 0
    assert runner.invoke(app, ["job", "list"]).exit_code == 0
    created = runner.invoke(app, ["job", "create", "GENERAL_CSC_RESEARCH"])
    assert created.exit_code == 0, created.output
    result = runner.invoke(app, ["worker", "once"])
    assert result.exit_code == 0, result.output
    assert '"status": "COMPLETED"' in result.stdout
    assert runner.invoke(app, ["worker", "once"]).exit_code == 0


def test_cli_job_inspection_does_not_expose_claim_token(container, settings, monkeypatch):
    monkeypatch.setenv("CM_DATABASE_URL", settings.database_url)
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    assert container.job_execution.claim_next("private-worker") is not None
    result = CliRunner().invoke(app, ["job", "get", str(job.id)])
    assert result.exit_code == 0
    assert '"worker_id": "private-worker"' in result.stdout
    assert "claim_token" not in result.stdout
