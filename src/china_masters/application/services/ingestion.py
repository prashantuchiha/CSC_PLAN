"""Transactional, evidence-first intake of structured professor research."""

from dataclasses import dataclass, replace
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.application.services.evidence import validate_fact
from china_masters.application.services.normalization import (
    normalized_doi,
    normalized_title,
    normalized_url,
)
from china_masters.domain.entities import (
    Professor,
    ProfessorContact,
    Publication,
    ResearchFact,
    Source,
)
from china_masters.domain.enums import ContactType, EntityType, VerificationStatus
from china_masters.domain.exceptions import NotFoundError, ReferenceError, ValidationError
from china_masters.domain.value_objects import JSONValue, utc_now


@dataclass(frozen=True)
class ContactFinding:
    contact_type: ContactType
    value: str
    source_url: str | None = None
    verified: bool = False
    notes: str | None = None


@dataclass(frozen=True)
class FactFinding:
    field_name: str
    value: JSONValue
    source_url: str
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: str | None = None


@dataclass(frozen=True)
class PublicationFinding:
    title: str
    year: int | None = None
    doi: str | None = None
    venue: str | None = None
    url: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class ProfessorResearchInput:
    university_id: UUID
    name_en: str
    professor_id: UUID | None = None
    name_zh: str | None = None
    department: str | None = None
    title: str | None = None
    official_profile_url: str | None = None
    sources: tuple[Source, ...] = ()
    contacts: tuple[ContactFinding, ...] = ()
    facts: tuple[FactFinding, ...] = ()
    publications: tuple[PublicationFinding, ...] = ()


@dataclass(frozen=True)
class IngestionResult:
    professor: Professor
    sources: tuple[Source, ...]
    contacts: tuple[ProfessorContact, ...]
    facts: tuple[ResearchFact, ...]
    publications: tuple[Publication, ...]


class ResearchIngestionService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def ingest_professor_research(self, command: ProfessorResearchInput) -> IngestionResult:
        if len(command.sources) > 50 or len(command.facts) > 100 or len(command.publications) > 100:
            raise ValidationError("Research batch exceeds intake limits")
        with self._uow() as uow:
            if uow.universities.get(command.university_id) is None:
                raise ReferenceError("University does not exist")
            if command.professor_id is None:
                professor = Professor(
                    university_id=command.university_id,
                    name_en=command.name_en,
                    name_zh=command.name_zh,
                    department=command.department,
                    title=command.title,
                    official_profile_url=command.official_profile_url,
                )
                uow.professors.add(professor)
            else:
                professor_candidate = uow.professors.get(command.professor_id)
                if professor_candidate is None:
                    raise NotFoundError("Professor does not exist")
                professor = professor_candidate
                if professor.university_id != command.university_id:
                    raise ValidationError("Professor belongs to another university")
                # Only explicit verified official facts may fill empty canonical fields.

            sources: dict[str, Source] = {}
            for source in command.sources:
                key = normalized_url(source.url)
                source_existing = uow.sources.by_normalized_url(key)
                if source_existing is None:
                    source_existing = replace(source, normalized_url=key)
                    uow.sources.add(source_existing)
                sources[key] = source_existing

            def source_for(url: str | None) -> Source | None:
                if url is None:
                    return None
                key = normalized_url(url)
                return sources.get(key) or uow.sources.by_normalized_url(key)

            contacts: list[ProfessorContact] = []
            known_contacts = uow.professor_contacts.for_professor(professor.id, limit=10000)
            for contact_finding in command.contacts:
                contact_source = source_for(contact_finding.source_url)
                if contact_finding.source_url is not None and contact_source is None:
                    raise ReferenceError("Contact source URL is not registered")
                contact = ProfessorContact(
                    professor_id=professor.id,
                    contact_type=contact_finding.contact_type,
                    value=contact_finding.value,
                    source_id=contact_source.id if contact_source else None,
                    verified=contact_finding.verified,
                    notes=contact_finding.notes,
                )
                contact_existing = next(
                    (
                        item
                        for item in known_contacts
                        if item.contact_type == contact.contact_type
                        and item.value.casefold() == contact.value.casefold()
                    ),
                    None,
                )
                if contact_existing is not None:
                    if contact.verified and not contact_existing.verified:
                        contact_existing = replace(
                            contact_existing,
                            verified=True,
                            source_id=contact.source_id,
                            notes=contact.notes or contact_existing.notes,
                        )
                        uow.professor_contacts.save(contact_existing)
                    contacts.append(contact_existing)
                else:
                    uow.professor_contacts.add(contact)
                    known_contacts.append(contact)
                    contacts.append(contact)

            facts: list[ResearchFact] = []
            canonical = {"name_en", "name_zh", "department", "title", "official_profile_url"}
            for fact_finding in command.facts:
                fact_source = source_for(fact_finding.source_url)
                if fact_source is None:
                    raise ReferenceError("Fact source URL is not registered")
                fact = validate_fact(
                    uow,
                    ResearchFact(
                        entity_type=EntityType.PROFESSOR,
                        entity_id=professor.id,
                        field_name=fact_finding.field_name,
                        value=fact_finding.value,
                        source_id=fact_source.id,
                        verification_status=fact_finding.verification_status,
                        notes=fact_finding.notes,
                    ),
                )
                uow.research_facts.add(fact)
                facts.append(fact)
                if (
                    command.professor_id is not None
                    and fact_finding.field_name in canonical
                    and fact_finding.verification_status == VerificationStatus.VERIFIED_OFFICIAL
                    and isinstance(fact_finding.value, str)
                    and fact_finding.value.strip()
                    and getattr(professor, fact_finding.field_name) is None
                ):
                    value = fact_finding.value
                    field = fact_finding.field_name
                    if field == "name_zh":
                        professor = replace(professor, name_zh=value)
                    elif field == "department":
                        professor = replace(professor, department=value)
                    elif field == "title":
                        professor = replace(professor, title=value)
                    elif field == "official_profile_url":
                        professor = replace(professor, official_profile_url=value)
                    professor = replace(professor, last_verified_at=utc_now(), updated_at=utc_now())
                    uow.professors.save(professor)

            publications: list[Publication] = []
            known_publications = uow.publications.for_professor(professor.id, limit=10000)
            for publication_finding in command.publications:
                publication_source = source_for(publication_finding.source_url)
                if publication_finding.source_url is not None and publication_source is None:
                    raise ReferenceError("Publication source URL is not registered")
                publication_existing = next(
                    (
                        item
                        for item in known_publications
                        if (
                            publication_finding.doi
                            and item.doi
                            and normalized_doi(publication_finding.doi) == normalized_doi(item.doi)
                        )
                        or (
                            item.year == publication_finding.year
                            and normalized_title(item.title)
                            == normalized_title(publication_finding.title)
                        )
                    ),
                    None,
                )
                if publication_existing is None:
                    publication_existing = Publication(
                        professor_id=professor.id,
                        title=publication_finding.title,
                        year=publication_finding.year,
                        doi=publication_finding.doi,
                        venue=publication_finding.venue,
                        url=publication_finding.url,
                        source_id=publication_source.id if publication_source else None,
                    )
                    uow.publications.add(publication_existing)
                    known_publications.append(publication_existing)
                publications.append(publication_existing)
            uow.commit()
            return IngestionResult(
                professor=professor,
                sources=tuple(sources.values()),
                contacts=tuple(contacts),
                facts=tuple(facts),
                publications=tuple(publications),
            )
