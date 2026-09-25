"""Deterministic synthetic provider. It never reads the network."""

from uuid import NAMESPACE_URL, uuid5

from china_masters.application.ports.integrations import ResearchResult
from china_masters.domain.entities import Professor, ResearchFact, Source, University
from china_masters.domain.enums import EntityType, SourceType


class FakeResearchProvider:
    def research_professor(self, professor: Professor) -> ResearchResult:
        url = f"https://example.invalid/professors/{professor.id.hex}"
        source = Source(
            id=uuid5(NAMESPACE_URL, url),
            url=url,
            source_type=SourceType.OTHER,
            title="Synthetic professor fixture",
        )
        fact = ResearchFact(
            id=uuid5(NAMESPACE_URL, url + "#summary"),
            entity_type=EntityType.PROFESSOR,
            entity_id=professor.id,
            field_name="research_summary",
            value=f"Synthetic research summary for {professor.name_en}",
            source_id=source.id,
        )
        return ResearchResult(sources=(source,), facts=(fact,))

    def research_university(self, university: University) -> ResearchResult:
        url = f"https://example.invalid/universities/{university.id.hex}"
        source = Source(
            id=uuid5(NAMESPACE_URL, url),
            url=url,
            source_type=SourceType.OTHER,
            title="Synthetic university fixture",
        )
        fact = ResearchFact(
            id=uuid5(NAMESPACE_URL, url + "#summary"),
            entity_type=EntityType.UNIVERSITY,
            entity_id=university.id,
            field_name="research_summary",
            value=f"Synthetic research summary for {university.canonical_name}",
            source_id=source.id,
        )
        return ResearchResult(sources=(source,), facts=(fact,))
