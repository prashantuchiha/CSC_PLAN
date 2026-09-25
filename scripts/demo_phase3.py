"""Disposable, entirely synthetic Phase 3 integration demonstration."""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import UUID

from alembic import command
from alembic.config import Config
from mcp import Client, StdioServerParameters

from china_masters.adapters.research.fake import FakeResearchProvider
from china_masters.application.services.ingestion import (
    ContactFinding,
    FactFinding,
    ProfessorResearchInput,
    PublicationFinding,
)
from china_masters.bootstrap import Container
from china_masters.domain.entities import Professor, Source, University
from china_masters.domain.enums import ContactType, SourceType, VerificationStatus
from china_masters.infrastructure.configuration.settings import Settings


async def mcp_roundtrip(
    project: Path, env: dict[str, str], a_id: str, b_id: str
) -> dict[str, object]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "china_masters.interfaces.cli.main", "mcp", "run"],
        cwd=project,
        env=env,
    )
    async with Client(params, raise_exceptions=True) as client:
        tools = await client.list_tools()
        professor = await client.call_tool("get_professor_research_context", {"professor_id": a_id})
        university = await client.call_tool(
            "get_university_research_context",
            {"university_id": professor.structured_content["professor"]["university_id"]},
        )
        publication = await client.call_tool(
            "add_publication",
            {"professor_id": b_id, "title": "Synthetic Systems Paper", "year": 2025},
        )
        jobs = await client.call_tool("create_research_jobs", {"professor_ids": [a_id, b_id]})
        notes = await client.call_tool(
            "save_professor_research_notes",
            {"professor_id": a_id, "content": "# Synthetic research notes\n"},
        )
        return {
            "server_tools": len(tools.tools),
            "professor_context_name": professor.structured_content["professor"]["name_en"],
            "university_context_programs": len(university.structured_content["programs"]),
            "mcp_publication_id": publication.structured_content["id"],
            "queued_job_ids": [item["id"] for item in jobs.structured_content["result"]],
            "note_path": notes.structured_content["relative_path"],
        }


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="china-masters-phase3-") as directory:
        root = Path(directory)
        database_url = f"sqlite:///{(root / 'demo.db').as_posix()}"
        env = os.environ.copy()
        env.update({"CM_DATABASE_URL": database_url, "CM_WORKSPACE_ROOT": str(root / "workspace")})
        configuration = Config(str(project / "alembic.ini"))
        configuration.attributes["database_url"] = database_url
        command.upgrade(configuration, "head")
        container = Container(
            Settings(database_url=database_url, workspace_root=root / "workspace", _env_file=None)
        )
        try:
            a = container.universities.create(University(canonical_name="Synthetic University A"))
            b = container.universities.create(University(canonical_name="Synthetic University B"))
            professor_a = container.professors.create(
                Professor(university_id=a.id, name_en="Wei Zhang", name_zh="张伟")
            )
            professor_b = container.professors.create(
                Professor(university_id=b.id, name_en="Li Chen", name_zh="陈丽")
            )
            official_url = "https://faculty.example.invalid/wei"
            intake = container.ingestion.ingest_professor_research(
                ProfessorResearchInput(
                    university_id=a.id,
                    professor_id=professor_a.id,
                    name_en=professor_a.name_en,
                    sources=(
                        Source(
                            url=official_url,
                            source_type=SourceType.OFFICIAL_FACULTY,
                            title="Synthetic faculty profile",
                        ),
                    ),
                    contacts=(
                        ContactFinding(
                            ContactType.EMAIL, "wei@example.invalid", official_url, True
                        ),
                    ),
                    facts=(
                        FactFinding(
                            "research_interest",
                            "distributed systems",
                            official_url,
                            VerificationStatus.VERIFIED_OFFICIAL,
                        ),
                    ),
                    publications=(
                        PublicationFinding(
                            "Synthetic Research Paper",
                            2024,
                            "10.0000/synthetic-wei",
                            source_url=official_url,
                        ),
                    ),
                )
            )
            fake_result = FakeResearchProvider().research_professor(professor_b)
            fake_intake = container.ingestion.ingest_professor_research(
                ProfessorResearchInput(
                    university_id=b.id,
                    professor_id=professor_b.id,
                    name_en=professor_b.name_en,
                    sources=fake_result.sources,
                    facts=tuple(
                        FactFinding(
                            fact.field_name,
                            fact.value,
                            fake_result.sources[0].url,
                            VerificationStatus.UNVERIFIED,
                        )
                        for fact in fake_result.facts
                    ),
                )
            )
            mcp = asyncio.run(mcp_roundtrip(project, env, str(professor_a.id), str(professor_b.id)))
            worker = subprocess.run(
                [sys.executable, "-m", "china_masters.interfaces.cli.main", "worker", "once"],
                cwd=project,
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            with container.uow() as uow:
                persisted = {
                    "universities": len(uow.universities.list()),
                    "professors": len(uow.professors.list()),
                    "sources": len(uow.sources.list()),
                    "facts": len(uow.research_facts.list()),
                    "publications": len(uow.publications.list()),
                    "contacts": len(uow.professor_contacts.list()),
                }
            output = {
                "synthetic": True,
                "universities": [str(a.id), str(b.id)],
                "professors": [str(professor_a.id), str(professor_b.id)],
                "official_source_id": str(intake.sources[0].id),
                "fake_fact_status": fake_intake.facts[0].verification_status.value,
                "professor_context_publications": len(
                    container.context.professor(professor_a.id)["recent_publications"]
                ),
                "university_context_professors": len(
                    container.context.university(a.id)["professors"]
                ),
                "mcp": mcp,
                "persisted": persisted,
                "worker_status": container.jobs.get(
                    UUID(json.loads(worker.stdout)["id"])
                ).status.value,
                "worker_output": json.loads(worker.stdout)["status"],
            }
            print(json.dumps(output, indent=2))
        finally:
            container.close()


if __name__ == "__main__":
    main()
