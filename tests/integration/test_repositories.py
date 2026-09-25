from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from china_masters.domain.entities import (
    ContactAttempt,
    EmailRecord,
    Professor,
    ProfessorContact,
    Program,
    Publication,
    ResearchFact,
    ResearchJob,
    Source,
    StudyPlan,
    University,
)
from china_masters.domain.enums import ContactType, EntityType, JobStatus, JobType, SourceType
from china_masters.domain.exceptions import ConflictError, ReferenceError


def test_all_repository_roundtrips_and_utc(container):
    university = University(canonical_name="Repository fixture")
    professor = Professor(university_id=university.id, name_en="Faculty")
    source = Source(url="https://example.invalid", source_type=SourceType.OTHER)
    email = EmailRecord(professor_id=professor.id, provider="future", subject="Metadata only")
    rows = [
        ("universities", university),
        ("professors", professor),
        ("sources", source),
        (
            "programs",
            Program(university_id=university.id, name="Computing", tuition_cny=Decimal("12000.50")),
        ),
        (
            "professor_contacts",
            ProfessorContact(
                professor_id=professor.id,
                contact_type=ContactType.ORCID,
                value="0000-0000-0000-0000",
                source_id=source.id,
            ),
        ),
        (
            "publications",
            Publication(professor_id=professor.id, title="Fixture", source_id=source.id),
        ),
        ("study_plans", StudyPlan(professor_id=professor.id, university_id=university.id)),
        ("email_records", email),
        (
            "contact_attempts",
            ContactAttempt(
                professor_id=professor.id,
                email_record_id=email.id,
                channel=ContactType.PROFESSIONAL_CONTACT_FORM,
                outcome="Recorded manually",
            ),
        ),
        (
            "research_facts",
            ResearchFact(
                entity_type=EntityType.PROFESSOR,
                entity_id=professor.id,
                field_name="example",
                value=None,
                source_id=source.id,
            ),
        ),
        ("research_jobs", ResearchJob(job_type=JobType.INBOX_SYNC)),
    ]
    with container.uow() as uow:
        for repository, row in rows:
            getattr(uow, repository).add(row)
        uow.commit()
    with container.uow() as uow:
        for repository, row in rows:
            stored = getattr(uow, repository).get(row.id)
            assert stored == row
            assert getattr(uow, repository).list() == [row]
        assert uow.universities.get(university.id).created_at.utcoffset().total_seconds() == 0
    updated = replace(university, notes="Updated metadata")
    with container.uow() as uow:
        uow.universities.save(updated)
        uow.commit()
    assert container.universities.get(university.id) == updated


def test_fk_is_enforced_below_services_and_transaction_rolls_back(container):
    university = University(canonical_name="Rollback")
    with pytest.raises(ReferenceError):
        with container.uow() as uow:
            uow.universities.add(university)
            uow.professors.add(Professor(university_id=uuid4(), name_en="Orphan"))
            uow.commit()
    assert container.universities.list() == []
    with container.engine.connect() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1


def test_uncommitted_changes_are_rolled_back(container):
    with container.uow() as uow:
        uow.universities.add(University(canonical_name="Never committed"))
    assert container.universities.list() == []


def test_duplicate_id_translates_to_conflict(container):
    university = container.universities.create(University(canonical_name="One"))
    with pytest.raises(ConflictError):
        container.universities.create(university)


def test_stale_job_update_cannot_overwrite_cancellation(container):
    original = ResearchJob(job_type=JobType.GENERAL_CSC_RESEARCH)
    with container.uow() as uow:
        uow.research_jobs.add(original)
        uow.commit()
    cancelled = container.jobs.cancel(original.id)
    with pytest.raises(ConflictError):
        with container.uow() as uow:
            uow.research_jobs.save(original.transition(JobStatus.RUNNING))
            uow.commit()
    assert container.jobs.get(original.id) == cancelled


def test_migration_upgrade_downgrade_and_metadata_match(container):
    config = Config("alembic.ini")
    config.attributes["database_url"] = container.settings.database_url
    assert len(inspect(container.engine).get_table_names()) == 12
    command.check(config)
    container.engine.dispose()
    command.downgrade(config, "base")
    assert inspect(container.engine).get_table_names() == ["alembic_version"]
    command.upgrade(config, "head")
    assert len(inspect(container.engine).get_table_names()) == 12
