from collections.abc import Callable
from types import TracebackType
from typing import Protocol

from china_masters.domain import repositories as repos


class UnitOfWork(Protocol):
    universities: repos.UniversityRepository
    programs: repos.ProgramRepository
    professors: repos.ProfessorRepository
    professor_contacts: repos.ProfessorContactRepository
    sources: repos.SourceRepository
    research_facts: repos.ResearchFactRepository
    publications: repos.PublicationRepository
    study_plans: repos.StudyPlanRepository
    email_records: repos.EmailRepository
    contact_attempts: repos.ContactAttemptRepository
    research_jobs: repos.ResearchJobRepository

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    def commit(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
