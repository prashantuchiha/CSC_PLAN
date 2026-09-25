from datetime import datetime

import pytest

from china_masters.domain.entities import ResearchJob, University
from china_masters.domain.enums import JobStatus, JobType
from china_masters.domain.exceptions import ValidationError


@pytest.mark.parametrize("target", [JobStatus.RUNNING, JobStatus.CANCELLED])
def test_queued_transitions(target):
    job = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH)
    changed = job.transition(target)
    assert job.status == JobStatus.QUEUED
    assert changed.status == target
    assert changed.revision == 1
    assert changed.attempts == int(target == JobStatus.RUNNING)


def test_retry_resets_timing_and_error():
    job = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH).transition(JobStatus.RUNNING)
    failed = job.transition(JobStatus.FAILED, error="test failure")
    assert failed.completed_at is not None
    retry = failed.transition(JobStatus.QUEUED)
    assert retry.started_at is retry.completed_at is retry.error_message is None
    running = retry.transition(JobStatus.RUNNING)
    assert running.attempts == 2
    assert running.started_at.utcoffset().total_seconds() == 0


def test_review_requires_requeue():
    running = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH).transition(JobStatus.RUNNING)
    review = running.transition(JobStatus.WAITING_FOR_REVIEW, result={"draft": "metadata"})
    with pytest.raises(ValidationError):
        review.transition(JobStatus.COMPLETED)
    assert review.transition(JobStatus.QUEUED).status == JobStatus.QUEUED


@pytest.mark.parametrize("initial", [JobStatus.COMPLETED, JobStatus.CANCELLED])
@pytest.mark.parametrize("target", list(JobStatus))
def test_terminal_states_cannot_transition(initial, target):
    job = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH, status=initial)
    with pytest.raises(ValidationError):
        job.transition(target)


def test_failure_requires_reason_and_results_have_valid_states():
    running = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH).transition(JobStatus.RUNNING)
    with pytest.raises(ValidationError):
        running.transition(JobStatus.FAILED)
    with pytest.raises(ValidationError):
        running.transition(JobStatus.CANCELLED, result={"unexpected": True})


def test_naive_timestamp_and_blank_name_rejected():
    with pytest.raises(ValidationError):
        University(canonical_name=" ")
    with pytest.raises(ValidationError):
        University(canonical_name="Example", created_at=datetime(2026, 1, 1))
