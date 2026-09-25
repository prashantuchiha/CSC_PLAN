"""Provider-neutral contracts. No integrations are executed in Phase 1."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from china_masters.domain.entities import Professor, ResearchFact, Source, University
from china_masters.domain.value_objects import JSONValue


@dataclass(frozen=True)
class ResearchResult:
    sources: tuple[Source, ...]
    facts: tuple[ResearchFact, ...]


@dataclass(frozen=True)
class StudyPlanContent:
    title: str
    sections: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EmailDraft:
    recipients: tuple[str, ...]
    subject: str
    body: str


@dataclass(frozen=True)
class ProviderMessage:
    message_id: str
    thread_id: str | None
    subject: str


@dataclass(frozen=True)
class MessagePage:
    messages: tuple[ProviderMessage, ...]
    next_cursor: str | None = None


class AIResearchProvider(Protocol):
    def research_university(self, university: University) -> ResearchResult: ...
    def research_professor(self, professor: Professor) -> ResearchResult: ...
    def generate_study_plan(
        self, professor: Professor, facts: tuple[ResearchFact, ...]
    ) -> StudyPlanContent: ...
    def draft_email(self, professor: Professor, facts: tuple[ResearchFact, ...]) -> EmailDraft: ...


class EmailProvider(Protocol):
    def create_draft(self, draft: EmailDraft) -> ProviderMessage: ...
    def send(self, message_id: str, *, idempotency_key: str) -> ProviderMessage: ...
    def list_inbox(self, *, cursor: str | None = None, limit: int = 100) -> MessagePage: ...
    def list_sent(self, *, cursor: str | None = None, limit: int = 100) -> MessagePage: ...
    def get_thread(self, thread_id: str) -> tuple[ProviderMessage, ...]: ...


class ResearchSourceProvider(Protocol):
    def search(self, query: str, *, limit: int = 10) -> tuple[Source, ...]: ...
    def retrieve(self, url: str) -> tuple[Source, bytes]: ...


class DocumentProvider(Protocol):
    def create_study_plan(self, content: StudyPlanContent) -> bytes: ...
    def update_study_plan(self, existing: bytes, content: StudyPlanContent) -> bytes: ...


class FileStorage(Protocol):
    def create_university_workspace(self, university_id: UUID, name: str) -> str: ...
    def create_professor_workspace(
        self, university_id: UUID, university_name: str, professor_id: UUID, professor_name: str
    ) -> str: ...
    def write_bytes(self, relative_path: str, content: bytes) -> str: ...
    def read_bytes(self, relative_path: str) -> bytes: ...


class JobDispatcher(Protocol):
    """Future worker wake-up hint; durable ResearchJob remains the source of truth.

    Invoke only after commit. Consumers must tolerate duplicate/lost hints and poll.
    A broker adapter can replace polling without changing job-producing services.
    """

    def notify(self, job_ids: tuple[UUID, ...], metadata: dict[str, JSONValue]) -> None: ...
