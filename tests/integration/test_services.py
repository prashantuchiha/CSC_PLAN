from dataclasses import replace
from uuid import uuid4

import pytest

from china_masters.application.commands.jobs import CreateJobs
from china_masters.domain.entities import Professor, ResearchFact, Source, University
from china_masters.domain.enums import (
    EntityType,
    JobStatus,
    JobType,
    SourceType,
    VerificationStatus,
)
from china_masters.domain.exceptions import NotFoundError, ReferenceError, ValidationError


def professor(container, university_name="Example"):
    university = container.universities.create(University(canonical_name=university_name))
    return container.professors.create(
        Professor(university_id=university.id, name_en="Example Faculty")
    )


def test_university_creation_retrieval_and_professor_workspace(container):
    faculty = professor(container)
    university = container.universities.get(faculty.university_id)
    assert university.canonical_name == "Example"
    assert container.professors.get(faculty.id) == faculty
    assert container.professors.list(university_id=university.id) == [faculty]
    path = container.workspaces.for_professor(faculty.id)
    assert container.workspaces.for_professor(faculty.id) == path
    assert {p.name for p in (container.settings.workspace_root / path).iterdir()} == {
        "sources",
        "research",
        "study_plans",
        "emails",
    }


def test_missing_references_and_not_found(container):
    with pytest.raises(ReferenceError):
        container.professors.create(Professor(university_id=uuid4(), name_en="Orphan"))
    with pytest.raises(NotFoundError):
        container.universities.get(uuid4())
    assert container.professors.list() == []


def test_source_and_verified_fact(container):
    faculty = professor(container)
    source = container.evidence.add_source(
        Source(url="https://example.invalid/faculty", source_type=SourceType.OFFICIAL_FACULTY)
    )
    fact = container.evidence.add_fact(
        ResearchFact(
            entity_type=EntityType.PROFESSOR,
            entity_id=faculty.id,
            field_name="research_summary",
            value={"topics": ["AI"]},
            source_id=source.id,
            verification_status=VerificationStatus.VERIFIED_OFFICIAL,
        )
    )
    assert fact.verified_at is not None
    assert container.evidence.get_source(source.id) == source
    assert container.evidence.list_facts() == [fact]
    with pytest.raises(ReferenceError):
        container.evidence.add_fact(replace(fact, id=uuid4(), source_id=uuid4()))
    with pytest.raises(ReferenceError):
        container.evidence.add_fact(replace(fact, id=uuid4(), entity_id=uuid4()))
    with pytest.raises(ValidationError):
        container.evidence.add_fact(
            replace(fact, id=uuid4(), verification_status=VerificationStatus.VERIFIED_PUBLICATION)
        )
    assert len(container.evidence.list_facts()) == 1


def test_single_global_job_and_lifecycle(container):
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.GENERAL_CSC_RESEARCH))
    assert container.jobs.get(job.id).status == JobStatus.QUEUED
    running = container.jobs.transition(job.id, JobStatus.RUNNING)
    assert running.attempts == 1
    completed = container.jobs.transition(job.id, JobStatus.COMPLETED, result={"count": 2})
    assert completed.result_json == {"count": 2}
    assert completed.completed_at is not None
    with pytest.raises(ValidationError):
        container.jobs.cancel(job.id)


def test_cross_university_batch_and_rollback(container):
    faculty = [professor(container, "A"), professor(container, "B"), professor(container, "B")]
    jobs = container.jobs.create(
        CreateJobs(
            job_type=JobType.PROFESSOR_RESEARCH,
            entity_ids=tuple(p.id for p in faculty),
            payload={"filters": ["machine learning"]},
        )
    )
    assert {job.entity_id for job in jobs} == {p.id for p in faculty}
    assert len({job.id for job in jobs}) == 3
    jobs[0].payload_json["filters"].append("changed")
    assert jobs[1].payload_json == {"filters": ["machine learning"]}
    assert container.jobs.get(jobs[0].id).payload_json == {"filters": ["machine learning"]}
    with pytest.raises(ReferenceError):
        container.jobs.create(
            CreateJobs(job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(faculty[0].id, uuid4()))
        )
    assert len(container.jobs.list()) == 3


def test_batch_validation_and_cancellation(container):
    faculty = professor(container)
    with pytest.raises(ValidationError):
        container.jobs.create(
            CreateJobs(job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(faculty.id, faculty.id))
        )
    with pytest.raises(ValidationError):
        container.jobs.create(CreateJobs(job_type=JobType.PROFESSOR_RESEARCH))
    with pytest.raises(ValidationError):
        container.jobs.create(
            CreateJobs(
                job_type=JobType.PROFESSOR_RESEARCH,
                entity_type=EntityType.UNIVERSITY,
                entity_ids=(faculty.university_id,),
            )
        )
    (job,) = container.jobs.create(CreateJobs(job_type=JobType.UNIVERSITY_DISCOVERY))
    cancelled = container.jobs.cancel(job.id)
    assert container.jobs.cancel(job.id) == cancelled
    assert container.jobs.list(status=JobStatus.CANCELLED) == [cancelled]
