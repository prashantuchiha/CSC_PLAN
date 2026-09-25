from datetime import datetime
from typing import Protocol
from uuid import UUID

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
from china_masters.domain.enums import JobStatus

from .base import Repository


class UniversityRepository(Repository[University], Protocol):
    pass


class ProgramRepository(Repository[Program], Protocol):
    def for_university(self, university_id: UUID, *, limit: int = 100) -> list[Program]: ...


class ProfessorRepository(Repository[Professor], Protocol):
    def for_university(
        self, university_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> list[Professor]: ...


class ProfessorContactRepository(Repository[ProfessorContact], Protocol):
    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[ProfessorContact]: ...


class SourceRepository(Repository[Source], Protocol):
    def by_normalized_url(self, url: str) -> Source | None: ...


class ResearchFactRepository(Repository[ResearchFact], Protocol):
    def for_entity(self, entity_id: UUID, *, limit: int = 100) -> list[ResearchFact]: ...


class PublicationRepository(Repository[Publication], Protocol):
    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[Publication]: ...


class StudyPlanRepository(Repository[StudyPlan], Protocol):
    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[StudyPlan]: ...


class EmailRepository(Repository[EmailRecord], Protocol):
    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[EmailRecord]: ...


class ContactAttemptRepository(Repository[ContactAttempt], Protocol):
    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[ContactAttempt]: ...


class ResearchJobRepository(Repository[ResearchJob], Protocol):
    def by_status(
        self, status: JobStatus, *, limit: int = 100, offset: int = 0
    ) -> list[ResearchJob]: ...

    def claim_next(
        self,
        *,
        worker_id: str,
        claim_token: UUID,
        now: datetime,
        lease_expires_at: datetime,
        max_attempts: int,
    ) -> ResearchJob | None: ...

    def expired(self, now: datetime, *, limit: int = 100) -> list[ResearchJob]: ...

    def exhausted_queued(self, max_attempts: int, *, limit: int = 100) -> list[ResearchJob]: ...
