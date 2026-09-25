from copy import deepcopy
from dataclasses import fields
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from china_masters.domain import entities
from china_masters.domain.enums import JobStatus
from china_masters.domain.exceptions import ConflictError
from china_masters.infrastructure.database import models

from .base import SQLAlchemyRepository


class SQLAlchemyUniversityRepository(
    SQLAlchemyRepository[entities.University, models.UniversityRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.University, models.UniversityRow)


class SQLAlchemyProgramRepository(SQLAlchemyRepository[entities.Program, models.ProgramRow]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.Program, models.ProgramRow)

    def for_university(self, university_id: UUID, *, limit: int = 100) -> list[entities.Program]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.university_id == university_id)
                .order_by(self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyProfessorRepository(SQLAlchemyRepository[entities.Professor, models.ProfessorRow]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.Professor, models.ProfessorRow)

    def for_university(
        self, university_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> list[entities.Professor]:
        rows = self.session.scalars(
            select(self.model)
            .where(self.model.university_id == university_id)
            .order_by(self.model.id)
            .limit(limit)
            .offset(offset)
        )
        return [self._entity(row) for row in rows]


class SQLAlchemyProfessorContactRepository(
    SQLAlchemyRepository[entities.ProfessorContact, models.ProfessorContactRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.ProfessorContact, models.ProfessorContactRow)

    def for_professor(
        self, professor_id: UUID, *, limit: int = 100
    ) -> list[entities.ProfessorContact]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.professor_id == professor_id)
                .order_by(self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemySourceRepository(SQLAlchemyRepository[entities.Source, models.SourceRow]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.Source, models.SourceRow)

    def by_normalized_url(self, url: str) -> entities.Source | None:
        row = self.session.scalar(select(self.model).where(self.model.normalized_url == url))
        return self._entity(row) if row is not None else None


class SQLAlchemyResearchFactRepository(
    SQLAlchemyRepository[entities.ResearchFact, models.ResearchFactRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.ResearchFact, models.ResearchFactRow)

    def for_entity(self, entity_id: UUID, *, limit: int = 100) -> list[entities.ResearchFact]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.entity_id == entity_id)
                .order_by(self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyPublicationRepository(
    SQLAlchemyRepository[entities.Publication, models.PublicationRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.Publication, models.PublicationRow)

    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[entities.Publication]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.professor_id == professor_id)
                .order_by(self.model.year.desc().nullslast(), self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyStudyPlanRepository(SQLAlchemyRepository[entities.StudyPlan, models.StudyPlanRow]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.StudyPlan, models.StudyPlanRow)

    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[entities.StudyPlan]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.professor_id == professor_id)
                .order_by(self.model.version.desc(), self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyEmailRepository(SQLAlchemyRepository[entities.EmailRecord, models.EmailRecordRow]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.EmailRecord, models.EmailRecordRow)

    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[entities.EmailRecord]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.professor_id == professor_id)
                .order_by(self.model.created_at.desc(), self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyContactAttemptRepository(
    SQLAlchemyRepository[entities.ContactAttempt, models.ContactAttemptRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.ContactAttempt, models.ContactAttemptRow)

    def for_professor(
        self, professor_id: UUID, *, limit: int = 100
    ) -> list[entities.ContactAttempt]:
        return [
            self._entity(row)
            for row in self.session.scalars(
                select(self.model)
                .where(self.model.professor_id == professor_id)
                .order_by(self.model.attempted_at.desc(), self.model.id)
                .limit(limit)
            )
        ]


class SQLAlchemyResearchJobRepository(
    SQLAlchemyRepository[entities.ResearchJob, models.ResearchJobRow]
):
    def __init__(self, session: Session) -> None:
        super().__init__(session, entities.ResearchJob, models.ResearchJobRow)

    def save(self, entity: entities.ResearchJob) -> None:
        values = {
            f.name: deepcopy(getattr(entity, f.name)) for f in fields(entity) if f.name != "id"
        }
        statement = (
            update(self.model)
            .where(
                self.model.id == entity.id,
                self.model.revision == entity.revision - 1,
            )
            .values(**values)
            .returning(self.model.id)
            .execution_options(synchronize_session=False)
        )
        if self.session.execute(statement).scalar_one_or_none() is None:
            raise ConflictError("Job changed concurrently; reload it before retrying")
        self.session.expire_all()

    def by_status(
        self, status: JobStatus, *, limit: int = 100, offset: int = 0
    ) -> list[entities.ResearchJob]:
        rows = self.session.scalars(
            select(self.model)
            .where(self.model.status == status)
            .order_by(self.model.priority.desc(), self.model.created_at, self.model.id)
            .limit(limit)
            .offset(offset)
        )
        return [self._entity(row) for row in rows]

    def claim_next(
        self,
        *,
        worker_id: str,
        claim_token: UUID,
        now: datetime,
        lease_expires_at: datetime,
        max_attempts: int,
    ) -> entities.ResearchJob | None:
        eligible = (
            select(self.model.id)
            .where(
                self.model.status == JobStatus.QUEUED,
                self.model.attempts < max_attempts,
                (self.model.next_attempt_at.is_(None)) | (self.model.next_attempt_at <= now),
            )
            .order_by(self.model.priority.desc(), self.model.created_at, self.model.id)
            .limit(1)
            .scalar_subquery()
        )
        statement = (
            update(self.model)
            .where(self.model.id == eligible, self.model.status == JobStatus.QUEUED)
            .values(
                status=JobStatus.RUNNING,
                worker_id=worker_id,
                claim_token=claim_token,
                lease_expires_at=lease_expires_at,
                next_attempt_at=None,
                started_at=now,
                completed_at=None,
                attempts=self.model.attempts + 1,
                revision=self.model.revision + 1,
            )
            .returning(self.model.id)
            .execution_options(synchronize_session=False)
        )
        claimed_id = self.session.execute(statement).scalar_one_or_none()
        if claimed_id is None:
            return None
        self.session.expire_all()
        return self.get(claimed_id)

    def expired(self, now: datetime, *, limit: int = 100) -> list[entities.ResearchJob]:
        rows = self.session.scalars(
            select(self.model)
            .where(
                self.model.status == JobStatus.RUNNING,
                self.model.lease_expires_at.is_not(None),
                self.model.lease_expires_at <= now,
            )
            .order_by(self.model.lease_expires_at, self.model.id)
            .limit(limit)
        )
        return [self._entity(row) for row in rows]

    def exhausted_queued(
        self, max_attempts: int, *, limit: int = 100
    ) -> list[entities.ResearchJob]:
        rows = self.session.scalars(
            select(self.model)
            .where(
                self.model.status == JobStatus.QUEUED,
                self.model.attempts >= max_attempts,
            )
            .order_by(self.model.created_at, self.model.id)
            .limit(limit)
        )
        return [self._entity(row) for row in rows]
