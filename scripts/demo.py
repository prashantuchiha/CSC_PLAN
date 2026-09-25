"""Idempotent synthetic fixture, explicitly requested for Phase 1 demonstration."""

import json
from dataclasses import asdict
from uuid import NAMESPACE_URL, uuid5

from china_masters.application.commands.jobs import CreateJobs
from china_masters.bootstrap import Container
from china_masters.domain.entities import Professor, ResearchFact, Source, University
from china_masters.domain.enums import EntityType, JobType, SourceType, VerificationStatus
from china_masters.infrastructure.configuration.settings import Settings


def main() -> None:
    container = Container(Settings())

    def identity(name):
        return uuid5(NAMESPACE_URL, "https://example.invalid/china-masters-demo/" + name)

    try:
        with container.uow() as uow:
            university = uow.universities.get(identity("university"))
        if university is None:
            university = container.universities.create(
                University(
                    id=identity("university"),
                    canonical_name="Demo University (synthetic)",
                    notes="Test fixture only; this is not verified real-world research.",
                )
            )
        professors = []
        for name in ("Demo Professor One", "Demo Professor Two"):
            with container.uow() as uow:
                professor = uow.professors.get(identity(name))
            if professor is None:
                professor = container.professors.create(
                    Professor(id=identity(name), university_id=university.id, name_en=name)
                )
            professors.append(professor)
            container.workspaces.for_professor(professor.id)
        with container.uow() as uow:
            source = uow.sources.get(identity("source"))
        if source is None:
            source = container.evidence.add_source(
                Source(
                    id=identity("source"),
                    url="https://example.invalid/synthetic-faculty-profile",
                    source_type=SourceType.OFFICIAL_FACULTY,
                    title="Synthetic evidence fixture",
                    notes="Demonstrates the verification workflow; not a real source.",
                )
            )
        with container.uow() as uow:
            fact = uow.research_facts.get(identity("fact"))
        if fact is None:
            fact = container.evidence.add_fact(
                ResearchFact(
                    id=identity("fact"),
                    entity_type=EntityType.PROFESSOR,
                    entity_id=professors[0].id,
                    field_name="research_summary",
                    value="Synthetic machine learning research example",
                    source_id=source.id,
                    verification_status=VerificationStatus.VERIFIED_OFFICIAL,
                    notes="Synthetic verification fixture, not a factual claim.",
                )
            )
        jobs = [job for job in container.jobs.list() if job.payload_json.get("demo") is True]
        if not jobs:
            jobs = container.jobs.create(
                CreateJobs(
                    job_type=JobType.PROFESSOR_RESEARCH,
                    entity_ids=tuple(p.id for p in professors),
                    payload={"demo": True},
                )
            )
        print(
            json.dumps(
                {
                    "university": asdict(university),
                    "professors": [asdict(p) for p in professors],
                    "source": asdict(source),
                    "fact": asdict(fact),
                    "jobs": [asdict(j) for j in jobs],
                },
                default=str,
                indent=2,
            )
        )
    finally:
        container.close()


if __name__ == "__main__":
    main()
