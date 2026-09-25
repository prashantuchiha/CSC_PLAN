"""Composition root: the only place that binds services to concrete infrastructure."""

from sqlalchemy.orm import sessionmaker

from china_masters.adapters.research.fake import FakeResearchProvider
from china_masters.application.dto.job_payloads import phase2_payload_registry
from china_masters.application.ports.unit_of_work import UnitOfWork
from china_masters.application.services.context import ResearchContextService
from china_masters.application.services.evidence import ResearchEvidenceService
from china_masters.application.services.ingestion import ResearchIngestionService
from china_masters.application.services.job_execution import JobExecutionService, JobPolicy
from china_masters.application.services.job_handlers import JobHandlerRegistry
from china_masters.application.services.jobs import JobService
from china_masters.application.services.professors import ProfessorService
from china_masters.application.services.records import (
    ContactAttemptService,
    EmailRecordService,
    ProfessorContactService,
    ProgramService,
    PublicationService,
    StudyPlanService,
)
from china_masters.application.services.universities import UniversityService
from china_masters.application.services.workspaces import WorkspaceService
from china_masters.infrastructure.configuration.settings import Settings
from china_masters.infrastructure.database.engine import build_engine
from china_masters.infrastructure.database.unit_of_work import SQLAlchemyUnitOfWork
from china_masters.infrastructure.filesystem.local import LocalFileStorage
from china_masters.workers.jobs.fake_handlers import (
    GeneralCSCResearchJobHandler,
    ProfessorResearchJobHandler,
    UniversityResearchJobHandler,
)
from china_masters.workers.jobs.worker import JobWorker


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.engine = build_engine(settings.database_url)
        self._sessions = sessionmaker(self.engine, expire_on_commit=False)
        self.job_policy = JobPolicy(
            max_attempts=settings.job_max_attempts,
            lease_seconds=settings.job_lease_seconds,
            poll_interval_seconds=settings.job_poll_interval_seconds,
        )
        self.universities = UniversityService(self.uow)
        self.professors = ProfessorService(self.uow)
        self.evidence = ResearchEvidenceService(self.uow)
        self.programs = ProgramService(self.uow)
        self.contacts = ProfessorContactService(self.uow)
        self.publications = PublicationService(self.uow)
        self.study_plans = StudyPlanService(self.uow)
        self.email_records = EmailRecordService(self.uow)
        self.contact_attempts = ContactAttemptService(self.uow)
        self.ingestion = ResearchIngestionService(self.uow)
        self.context = ResearchContextService(self.uow)
        self.jobs = JobService(self.uow, phase2_payload_registry(), self.job_policy)
        self.job_execution = JobExecutionService(self.uow, self.job_policy)
        self.workspaces = WorkspaceService(
            LocalFileStorage(settings.workspace_root), self.universities, self.professors
        )

    def uow(self) -> UnitOfWork:
        return SQLAlchemyUnitOfWork(self._sessions)

    def create_worker(self) -> JobWorker:
        provider = FakeResearchProvider()
        handlers = JobHandlerRegistry(
            (
                ProfessorResearchJobHandler(self.professors, provider),
                UniversityResearchJobHandler(self.universities, provider),
                GeneralCSCResearchJobHandler(),
            )
        )
        return JobWorker(self.job_execution, handlers)

    def close(self) -> None:
        self.engine.dispose()
