from dataclasses import replace
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory
from china_masters.application.queries.pagination import Page
from china_masters.application.services.normalization import normalized_url
from china_masters.application.services.references import require_reference
from china_masters.domain.entities import ResearchFact, Source
from china_masters.domain.enums import SourceType, VerificationStatus
from china_masters.domain.exceptions import NotFoundError, ReferenceError, ValidationError
from china_masters.domain.value_objects import utc_now


def validate_fact(uow: UnitOfWork, fact: ResearchFact) -> ResearchFact:
    require_reference(uow, fact.entity_type, fact.entity_id)
    source = uow.sources.get(fact.source_id)
    if source is None:
        raise ReferenceError(f"Source {fact.source_id} does not exist")
    official = {
        SourceType.OFFICIAL_UNIVERSITY,
        SourceType.OFFICIAL_GOVERNMENT,
        SourceType.OFFICIAL_FACULTY,
        SourceType.OFFICIAL_LAB,
    }
    allowed = {
        VerificationStatus.VERIFIED_OFFICIAL: official,
        VerificationStatus.VERIFIED_PUBLICATION: {SourceType.PUBLICATION},
        VerificationStatus.VERIFIED_SECONDARY: {SourceType.SECONDARY, SourceType.ACADEMIC_INDEX},
    }
    if fact.verification_status in allowed:
        if source.source_type not in allowed[fact.verification_status]:
            raise ValidationError("Verification status does not match the source type")
        return replace(fact, verified_at=fact.verified_at or utc_now())
    return fact


class ResearchEvidenceService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def add_source(self, source: Source) -> Source:
        key = normalized_url(source.url)
        with self._uow() as uow:
            existing = uow.sources.by_normalized_url(key)
            if existing is not None:
                return existing
            source = replace(source, normalized_url=key)
            uow.sources.add(source)
            uow.commit()
        return source

    def get_source(self, source_id: UUID) -> Source:
        with self._uow() as uow:
            source = uow.sources.get(source_id)
            if source is None:
                raise NotFoundError(f"Source {source_id} does not exist")
            return source

    def add_fact(self, fact: ResearchFact) -> ResearchFact:
        with self._uow() as uow:
            fact = validate_fact(uow, fact)
            uow.research_facts.add(fact)
            uow.commit()
        return fact

    def list_facts(self, page: Page = Page()) -> list[ResearchFact]:
        with self._uow() as uow:
            return uow.research_facts.list(limit=page.limit, offset=page.offset)

    def for_entity(self, entity_id: UUID, *, limit: int = 100) -> list[ResearchFact]:
        with self._uow() as uow:
            return uow.research_facts.for_entity(entity_id, limit=limit)
