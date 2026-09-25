"""stdio MCP tools delegate all persistence and rules to application services."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from china_masters.application.commands.jobs import CreateJobs
from china_masters.application.queries.pagination import Page
from china_masters.application.services.ingestion import (
    ContactFinding,
    FactFinding,
    ProfessorResearchInput,
    PublicationFinding,
)
from china_masters.bootstrap import Container
from china_masters.domain.entities import (
    Professor,
    ProfessorContact,
    Publication,
    ResearchFact,
    Source,
    University,
)
from china_masters.domain.enums import (
    ContactType,
    EntityType,
    JobStatus,
    JobType,
    SourceType,
    VerificationStatus,
)
from china_masters.domain.exceptions import DomainError

P = ParamSpec("P")
R = TypeVar("R")


def dto(value: object) -> Any:
    return jsonable_encoder(value)


class SourceInput(BaseModel):
    url: str
    source_type: SourceType
    title: str | None = None
    publisher: str | None = None
    domain: str | None = None
    retrieved_at: datetime | None = None
    published_at: datetime | None = None
    content_hash: str | None = None
    local_snapshot_path: str | None = None
    notes: str | None = None


class ContactInput(BaseModel):
    contact_type: ContactType
    value: str
    source_url: str | None = None
    verified: bool = False
    notes: str | None = None


class FactInput(BaseModel):
    field_name: str
    value: Any
    source_url: str
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: str | None = None


class PublicationInput(BaseModel):
    title: str
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    url: str | None = None
    source_url: str | None = None


class IngestInput(BaseModel):
    university_id: UUID
    name_en: str
    professor_id: UUID | None = None
    name_zh: str | None = None
    department: str | None = None
    title: str | None = None
    official_profile_url: str | None = None
    sources: list[SourceInput] = Field(default_factory=list, max_length=50)
    contacts: list[ContactInput] = Field(default_factory=list, max_length=100)
    facts: list[FactInput] = Field(default_factory=list, max_length=100)
    publications: list[PublicationInput] = Field(default_factory=list, max_length=100)


def create_server(container: Container) -> MCPServer:
    mcp = MCPServer(
        "China Masters Research OS",
        version="0.3.0",
        instructions="Local research records; evidence is sourced and may conflict.",
    )

    def register(fn: Callable[P, R]) -> Callable[P, R]:
        @wraps(fn)
        def safe(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return fn(*args, **kwargs)
            except DomainError as exc:
                raise ToolError(f"{type(exc).__name__}: {exc}") from None

        return mcp.tool()(safe)

    @register
    def search_universities(query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Find universities by name, abbreviation, or city."""
        return dto(container.universities.search(query, limit=limit))

    @register
    def get_university(university_id: UUID) -> dict[str, Any]:
        """Get one university."""
        return dto(container.universities.get(university_id))

    @register
    def create_university(
        canonical_name: str, chinese_name: str | None = None, city: str | None = None
    ) -> dict[str, Any]:
        """Create a university record."""
        return dto(
            container.universities.create(
                University(canonical_name=canonical_name, chinese_name=chinese_name, city=city)
            )
        )

    @register
    def update_university(
        university_id: UUID,
        canonical_name: str | None = None,
        chinese_name: str | None = None,
        city: str | None = None,
    ) -> dict[str, Any]:
        """Explicitly edit selected university identity fields."""
        current = container.universities.get(university_id)
        updated = replace(
            current,
            canonical_name=canonical_name or current.canonical_name,
            chinese_name=chinese_name if chinese_name is not None else current.chinese_name,
            city=city if city is not None else current.city,
        )
        return dto(container.universities.update(updated))

    @register
    def get_university_research_context(
        university_id: UUID,
        professor_limit: int = 20,
        program_limit: int = 20,
        source_limit: int = 10,
    ) -> dict[str, Any]:
        """Bounded programs, admission evidence, professors and sources."""
        return dto(
            container.context.university(
                university_id,
                professor_limit=professor_limit,
                program_limit=program_limit,
                source_limit=source_limit,
            )
        )

    @register
    def search_professors(
        query: str, university_id: UUID | None = None, limit: int = 20
    ) -> list[dict[str, Any]]:
        """Find possible identity matches by names, profile or academic contact IDs."""
        return dto(container.professors.search(query, university_id=university_id, limit=limit))

    @register
    def list_professors(
        university_id: UUID | None = None, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List professors with pagination."""
        return dto(container.professors.list(Page(limit, offset), university_id=university_id))

    @register
    def get_professor(professor_id: UUID) -> dict[str, Any]:
        """Get one professor."""
        return dto(container.professors.get(professor_id))

    @register
    def create_professor(
        university_id: UUID, name_en: str, name_zh: str | None = None, department: str | None = None
    ) -> dict[str, Any]:
        """Create a professor without automatic name-based merging."""
        return dto(
            container.professors.create(
                Professor(
                    university_id=university_id,
                    name_en=name_en,
                    name_zh=name_zh,
                    department=department,
                )
            )
        )

    @register
    def update_professor(
        professor_id: UUID,
        department: str | None = None,
        title: str | None = None,
        name_zh: str | None = None,
    ) -> dict[str, Any]:
        """Explicit manual correction of selected canonical professor fields."""
        current = container.professors.get(professor_id)
        updated = replace(
            current,
            department=department if department is not None else current.department,
            title=title if title is not None else current.title,
            name_zh=name_zh if name_zh is not None else current.name_zh,
        )
        return dto(container.professors.update(updated))

    @register
    def get_professor_research_context(
        professor_id: UUID, publication_limit: int = 10, source_limit: int = 10
    ) -> dict[str, Any]:
        """Bounded professor evidence, contacts, publications and outreach."""
        return dto(
            container.context.professor(
                professor_id, publication_limit=publication_limit, source_limit=source_limit
            )
        )

    @register
    def ingest_professor_research(input: IngestInput) -> dict[str, Any]:
        """Persist sourced findings transactionally; conflicting claims coexist."""
        command = ProfessorResearchInput(
            university_id=input.university_id,
            professor_id=input.professor_id,
            name_en=input.name_en,
            name_zh=input.name_zh,
            department=input.department,
            title=input.title,
            official_profile_url=input.official_profile_url,
            sources=tuple(Source(**item.model_dump(exclude_none=True)) for item in input.sources),
            contacts=tuple(ContactFinding(**item.model_dump()) for item in input.contacts),
            facts=tuple(FactFinding(**item.model_dump()) for item in input.facts),
            publications=tuple(
                PublicationFinding(**item.model_dump()) for item in input.publications
            ),
        )
        return dto(container.ingestion.ingest_professor_research(command))

    @register
    def add_source(input: SourceInput) -> dict[str, Any]:
        """Add or reuse a source by conservative URL identity."""
        return dto(container.evidence.add_source(Source(**input.model_dump(exclude_none=True))))

    @register
    def add_research_fact(
        entity_type: EntityType,
        entity_id: UUID,
        field_name: str,
        value: Any,
        source_id: UUID,
        verification_status: VerificationStatus = VerificationStatus.UNVERIFIED,
    ) -> dict[str, Any]:
        """Add a sourced fact without rewriting canonical fields."""
        return dto(
            container.evidence.add_fact(
                ResearchFact(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    field_name=field_name,
                    value=value,
                    source_id=source_id,
                    verification_status=verification_status,
                )
            )
        )

    @register
    def add_publication(
        professor_id: UUID,
        title: str,
        year: int | None = None,
        doi: str | None = None,
        source_id: UUID | None = None,
    ) -> dict[str, Any]:
        """Add a publication, reusing obvious DOI/title duplicates."""
        return dto(
            container.publications.add(
                Publication(
                    professor_id=professor_id, title=title, year=year, doi=doi, source_id=source_id
                )
            )
        )

    @register
    def add_professor_contact(
        professor_id: UUID,
        contact_type: ContactType,
        value: str,
        source_id: UUID | None = None,
        verified: bool = False,
        notes: str | None = None,
    ) -> dict[str, Any]:
        """Add a public academic contact with optional provenance."""
        return dto(
            container.contacts.add(
                ProfessorContact(
                    professor_id=professor_id,
                    contact_type=contact_type,
                    value=value,
                    source_id=source_id,
                    verified=verified,
                    notes=notes,
                )
            )
        )

    @register
    def get_professor_sources(professor_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
        """List source references in a bounded professor context."""
        return dto(container.context.professor_sources(professor_id, limit=limit))

    @register
    def create_research_jobs(professor_ids: list[UUID], priority: int = 0) -> list[dict[str, Any]]:
        """Queue professor research jobs across universities; worker runs separately."""
        return dto(
            container.jobs.create(
                CreateJobs(
                    job_type=JobType.PROFESSOR_RESEARCH,
                    entity_type=EntityType.PROFESSOR,
                    entity_ids=tuple(professor_ids),
                    priority=priority,
                )
            )
        )

    @register
    def get_jobs(status: JobStatus | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """List jobs and their current durable states."""
        return dto(container.jobs.list(Page(limit, 0), status=status))

    @register
    def get_job(job_id: UUID) -> dict[str, Any]:
        """Get one durable job."""
        return dto(container.jobs.get(job_id))

    @register
    def get_pending_research(limit: int = 20) -> list[dict[str, Any]]:
        """List queued research jobs."""
        return dto(container.jobs.list(Page(limit, 0), status=JobStatus.QUEUED))

    @register
    def get_stale_research(
        days: int = 180, kind: str = "professors", limit: int = 100
    ) -> list[dict[str, Any]]:
        """Find professors or universities lacking recent verification."""
        if kind == "professors":
            return dto(container.context.stale_professors(days, limit=limit))
        if kind == "universities":
            return dto(container.context.stale_universities(days, limit=limit))
        raise ValueError("kind must be professors or universities")

    @register
    def create_professor_workspace(professor_id: UUID) -> dict[str, str]:
        """Create the safe standard workspace for a professor."""
        return {"relative_path": container.workspaces.for_professor(professor_id)}

    @register
    def save_professor_research_notes(
        professor_id: UUID, content: str, kind: str = "notes"
    ) -> dict[str, str]:
        """Save bounded Markdown notes or summary in the standard research folder."""
        return {
            "relative_path": container.workspaces.save_professor_research_notes(
                professor_id, content, kind=kind
            )
        }

    @mcp.resource("research://professors/{professor_id}")
    def professor_context_resource(professor_id: str) -> str:
        """Compact professor research context."""
        import json

        return json.dumps(dto(container.context.professor(UUID(professor_id))), ensure_ascii=False)

    @mcp.resource("research://universities/{university_id}")
    def university_context_resource(university_id: str) -> str:
        """Compact university research context."""
        import json

        return json.dumps(
            dto(container.context.university(UUID(university_id))), ensure_ascii=False
        )

    return mcp
