from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from china_masters.domain import repositories as contracts
from china_masters.infrastructure.database import repositories as repos
from china_masters.infrastructure.database.repositories.base import translate_integrity


class SQLAlchemyUnitOfWork:
    universities: contracts.UniversityRepository
    programs: contracts.ProgramRepository
    professors: contracts.ProfessorRepository
    professor_contacts: contracts.ProfessorContactRepository
    sources: contracts.SourceRepository
    research_facts: contracts.ResearchFactRepository
    publications: contracts.PublicationRepository
    study_plans: contracts.StudyPlanRepository
    email_records: contracts.EmailRepository
    contact_attempts: contracts.ContactAttemptRepository
    research_jobs: contracts.ResearchJobRepository

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "SQLAlchemyUnitOfWork":
        self._session = self._session_factory()
        self.universities = repos.SQLAlchemyUniversityRepository(self._session)
        self.programs = repos.SQLAlchemyProgramRepository(self._session)
        self.professors = repos.SQLAlchemyProfessorRepository(self._session)
        self.professor_contacts = repos.SQLAlchemyProfessorContactRepository(self._session)
        self.sources = repos.SQLAlchemySourceRepository(self._session)
        self.research_facts = repos.SQLAlchemyResearchFactRepository(self._session)
        self.publications = repos.SQLAlchemyPublicationRepository(self._session)
        self.study_plans = repos.SQLAlchemyStudyPlanRepository(self._session)
        self.email_records = repos.SQLAlchemyEmailRepository(self._session)
        self.contact_attempts = repos.SQLAlchemyContactAttemptRepository(self._session)
        self.research_jobs = repos.SQLAlchemyResearchJobRepository(self._session)
        return self

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as error:
            translate_integrity(error)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._session.rollback()
        finally:
            self._session.close()
