import asyncio
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from mcp import Client
from sqlalchemy import create_engine, text

from china_masters.application.services.ingestion import (
    ContactFinding,
    FactFinding,
    ProfessorResearchInput,
    PublicationFinding,
)
from china_masters.domain.entities import (
    ContactAttempt,
    EmailRecord,
    Professor,
    ProfessorContact,
    Program,
    Publication,
    ResearchFact,
    Source,
    StudyPlan,
    University,
)
from china_masters.domain.enums import ContactType, EntityType, SourceType, VerificationStatus
from china_masters.domain.exceptions import ReferenceError, ValidationError
from china_masters.interfaces.mcp.server import create_server

ROOT = Path(__file__).resolve().parents[2]


def test_remaining_record_services(container):
    university = container.universities.create(University(canonical_name="Example University"))
    professor = container.professors.create(
        Professor(university_id=university.id, name_en="Wei Zhang")
    )
    program = container.programs.create(Program(university_id=university.id, name="CS MSc"))
    assert container.programs.get(program.id) == program
    assert container.programs.for_university(university.id) == [program]
    assert container.programs.update(replace(program, notes="CSC eligible")).notes == "CSC eligible"
    source = container.evidence.add_source(
        Source(url="https://example.invalid/faculty/wei", source_type=SourceType.OFFICIAL_FACULTY)
    )
    contact = container.contacts.add(
        ProfessorContact(
            professor_id=professor.id,
            contact_type=ContactType.EMAIL,
            value="wei@example.invalid",
            source_id=source.id,
            verified=True,
        )
    )
    assert container.contacts.for_professor(professor.id) == [contact]
    first = container.publications.add(
        Publication(professor_id=professor.id, title="A Paper", year=2024, doi="10.1/ABC")
    )
    duplicate = container.publications.add(
        Publication(
            professor_id=professor.id,
            title="Different title",
            year=2024,
            doi="https://doi.org/10.1/abc",
        )
    )
    assert duplicate.id == first.id
    assert len(container.publications.for_professor(professor.id)) == 1
    plan = container.study_plans.create(StudyPlan(professor_id=professor.id))
    assert container.study_plans.for_professor(professor.id)[0].id == plan.id
    email = container.email_records.create(
        EmailRecord(professor_id=professor.id, provider="local", subject="Inquiry")
    )
    attempt = container.contact_attempts.create(
        ContactAttempt(
            professor_id=professor.id,
            channel=ContactType.EMAIL,
            outcome="drafted",
            email_record_id=email.id,
        )
    )
    assert container.email_records.for_professor(professor.id)[0].id == email.id
    assert container.contact_attempts.for_professor(professor.id)[0].id == attempt.id


def test_ingestion_dedup_evidence_conflicts_and_rollback(container):
    university = container.universities.create(University(canonical_name="Example University"))
    professor = container.professors.create(
        Professor(university_id=university.id, name_en="Wei Zhang", title="Professor")
    )
    url = "HTTPS://EXAMPLE.INVALID:443/faculty/wei#bio"
    source = Source(
        url=url,
        source_type=SourceType.OFFICIAL_FACULTY,
        title="Faculty page",
        publisher="Example University",
        content_hash="abc",
    )
    command = ProfessorResearchInput(
        university_id=university.id,
        professor_id=professor.id,
        name_en="Wei Zhang",
        sources=(source,),
        contacts=(ContactFinding(ContactType.EMAIL, "wei@example.invalid", url, True),),
        facts=(
            FactFinding("title", "Dean", url, VerificationStatus.UNVERIFIED),
            FactFinding("title", "Chair", url, VerificationStatus.CONFLICTING),
            FactFinding("title", "Director", url, VerificationStatus.VERIFIED_OFFICIAL),
            FactFinding(
                "department", "Computer Science", url, VerificationStatus.VERIFIED_OFFICIAL
            ),
        ),
        publications=(PublicationFinding("A Paper", 2024, "10.1/test", source_url=url),),
    )
    result = container.ingestion.ingest_professor_research(command)
    assert result.professor.title == "Professor"
    assert {fact.value for fact in result.facts} == {
        "Dean",
        "Chair",
        "Director",
        "Computer Science",
    }
    assert result.professor.department == "Computer Science"
    assert result.professor.last_verified_at is not None
    assert result.contacts[0].source_id == result.sources[0].id
    assert result.publications[0].source_id == result.sources[0].id
    reused = container.evidence.add_source(
        Source(url="https://example.invalid/faculty/wei", source_type=SourceType.SECONDARY)
    )
    assert reused.id == result.sources[0].id
    assert reused.title == "Faculty page" and reused.content_hash == "abc"
    assert len(container.ingestion.ingest_professor_research(command).publications) == 1
    assert len(container.publications.for_professor(professor.id)) == 1
    with pytest.raises(ReferenceError):
        container.ingestion.ingest_professor_research(
            ProfessorResearchInput(
                university_id=university.id,
                name_en="Rollback Example",
                sources=(
                    Source(url="https://example.invalid/new", source_type=SourceType.SECONDARY),
                ),
                facts=(FactFinding("interest", "AI", "https://example.invalid/missing"),),
            )
        )
    assert container.professors.search("Rollback") == []
    with container.uow() as uow:
        assert uow.sources.by_normalized_url("https://example.invalid/new") is None


def test_context_freshness_and_safe_notes(container, settings):
    university = container.universities.create(University(canonical_name="Example University"))
    professor = container.professors.create(
        Professor(university_id=university.id, name_en="Wei Zhang")
    )
    source = container.evidence.add_source(
        Source(url="https://example.invalid/faculty", source_type=SourceType.OFFICIAL_FACULTY)
    )
    for year in range(2020, 2030):
        container.publications.add(
            Publication(professor_id=professor.id, title=f"Paper {year}", year=year)
        )
    container.evidence.add_fact(
        ResearchFact(
            entity_type=EntityType.PROFESSOR,
            entity_id=professor.id,
            field_name="interest",
            value="AI",
            source_id=source.id,
            verification_status=VerificationStatus.VERIFIED_OFFICIAL,
        )
    )
    context = container.context.professor(professor.id, publication_limit=2, source_limit=1)
    assert len(context["recent_publications"]) == 2
    assert len(context["sources"]) == 1
    assert context["last_verified_at"] is not None
    assert len(container.context.university(university.id, professor_limit=1)["professors"]) == 1
    assert container.context.stale_professors(180) == []
    assert container.context.stale_universities(180)[0]["id"] == university.id
    path = container.workspaces.save_professor_research_notes(professor.id, "# Notes")
    assert (settings.workspace_root / path).read_text() == "# Notes"
    with pytest.raises(ValidationError):
        container.workspaces.save_professor_research_notes(professor.id, "bad", kind="../evil")
    with pytest.raises(ValidationError):
        container.workspaces.save_professor_research_notes(professor.id, "x" * 100001)


def test_mcp_tools_resources_and_safety(container, settings):
    async def exercise():
        async with Client(create_server(container), raise_exceptions=True) as client:
            tools = await client.list_tools()
            names = {item.name for item in tools.tools}
            assert len(names) == 24
            assert "execute_sql" not in names and "arbitrary_filesystem_write" not in names
            a = await client.call_tool("create_university", {"canonical_name": "University A"})
            b = await client.call_tool("create_university", {"canonical_name": "University B"})
            a_id = a.structured_content["id"]
            b_id = b.structured_content["id"]
            p1 = await client.call_tool(
                "create_professor", {"university_id": a_id, "name_en": "Wei Zhang"}
            )
            p2 = await client.call_tool(
                "create_professor", {"university_id": b_id, "name_en": "Li Chen"}
            )
            p1_id = p1.structured_content["id"]
            p2_id = p2.structured_content["id"]
            source = await client.call_tool(
                "add_source",
                {
                    "input": {
                        "url": "https://example.invalid/wei",
                        "source_type": "OFFICIAL_FACULTY",
                    }
                },
            )
            ingested = await client.call_tool(
                "ingest_professor_research",
                {
                    "input": {
                        "university_id": a_id,
                        "professor_id": p1_id,
                        "name_en": "Wei Zhang",
                        "facts": [
                            {
                                "field_name": "interest",
                                "value": "AI",
                                "source_url": "https://example.invalid/wei",
                                "verification_status": "VERIFIED_OFFICIAL",
                            }
                        ],
                    }
                },
            )
            assert len(ingested.structured_content["facts"]) == 1
            await client.call_tool(
                "add_professor_contact",
                {
                    "professor_id": p1_id,
                    "contact_type": "EMAIL",
                    "value": "wei@example.invalid",
                    "source_id": source.structured_content["id"],
                    "verified": True,
                },
            )
            context = await client.call_tool(
                "get_professor_research_context", {"professor_id": p1_id}
            )
            assert context.structured_content["professor"]["name_en"] == "Wei Zhang"
            assert len(context.structured_content["verified_contacts"]) == 1
            await client.call_tool(
                "save_professor_research_notes", {"professor_id": p1_id, "content": "# Research"}
            )
            bad = await client.call_tool(
                "save_professor_research_notes",
                {"professor_id": p1_id, "content": "bad", "kind": "../../evil"},
            )
            assert bad.is_error
            assert "ValidationError" in bad.content[0].text
            jobs = await client.call_tool("create_research_jobs", {"professor_ids": [p1_id, p2_id]})
            assert len(jobs.structured_content["result"]) == 2
            resource = await client.read_resource(f"research://professors/{p1_id}")
            assert "Wei Zhang" in resource.contents[0].text
            return p1_id, p2_id

    p1_id, p2_id = asyncio.run(exercise())
    assert str(container.jobs.list()[0].entity_id) in {p1_id, p2_id}
    assert not (settings.workspace_root / "evil").exists()


def test_api_phase3_workflows(client):
    university = client.post("/universities", json={"canonical_name": "Example University"}).json()
    professor = client.post(
        "/professors", json={"university_id": university["id"], "name_en": "Wei Zhang"}
    ).json()
    program = client.post(
        f"/universities/{university['id']}/programs", json={"name": "Computer Science MSc"}
    )
    assert program.status_code == 201
    publication = client.post(
        f"/professors/{professor['id']}/publications", json={"title": "A Paper", "year": 2024}
    )
    assert publication.status_code == 201
    assert len(client.get(f"/professors/{professor['id']}/publications").json()) == 1
    assert len(client.get(f"/universities/{university['id']}/programs").json()) == 1
    assert (
        client.get(f"/professors/{professor['id']}/context").json()["recent_publications"][0][
            "title"
        ]
        == "A Paper"
    )


def test_source_migration_preserves_historical_duplicates(tmp_path):
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database.as_posix()}"
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = url
    command.upgrade(config, "ee8576e1a3fb")
    first, second = uuid4().hex, uuid4().hex
    engine = create_engine(url)
    with engine.begin() as connection:
        for source_id, source_url in (
            (first, "HTTPS://EXAMPLE.INVALID:443/path#one"),
            (second, "https://example.invalid/path"),
        ):
            connection.execute(
                text(
                    "INSERT INTO sources (id, url, source_type, retrieved_at) "
                    "VALUES (:id, :url, :type, :date)"
                ),
                {
                    "id": source_id,
                    "url": source_url,
                    "type": "OFFICIAL_FACULTY",
                    "date": "2024-01-01 00:00:00",
                },
            )
    command.upgrade(config, "head")
    with engine.connect() as connection:
        rows = connection.execute(text("SELECT id, normalized_url FROM sources ORDER BY id")).all()
    assert len(rows) == 2
    assert [key for _, key in rows if key is not None] == ["https://example.invalid/path"]
    engine.dispose()
