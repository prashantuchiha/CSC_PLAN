"""Small, structured research views for human and model clients."""

from dataclasses import asdict
from datetime import datetime, timedelta
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.domain.entities import ResearchFact, Source
from china_masters.domain.enums import VerificationStatus
from china_masters.domain.exceptions import NotFoundError, ValidationError
from china_masters.domain.value_objects import utc_now


def _limit(value: int, maximum: int) -> int:
    if not 1 <= value <= maximum:
        raise ValidationError(f"Limit must be 1..{maximum}")
    return value


def _verified_at(facts: list[ResearchFact]) -> datetime | None:
    dates = [
        fact.verified_at
        for fact in facts
        if fact.verified_at is not None
        and fact.verification_status
        in {
            VerificationStatus.VERIFIED_OFFICIAL,
            VerificationStatus.VERIFIED_PUBLICATION,
            VerificationStatus.VERIFIED_SECONDARY,
        }
    ]
    return max(dates) if dates else None


class ResearchContextService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def professor(
        self,
        professor_id: UUID,
        *,
        publication_limit: int = 10,
        source_limit: int = 10,
        fact_limit: int = 30,
    ) -> dict[str, object]:
        _limit(publication_limit, 50)
        _limit(source_limit, 50)
        _limit(fact_limit, 100)
        with self._uow() as uow:
            professor = uow.professors.get(professor_id)
            if professor is None:
                raise NotFoundError("Professor does not exist")
            university = uow.universities.get(professor.university_id)
            assert university is not None
            facts = uow.research_facts.for_entity(professor_id, limit=fact_limit)
            facts = [fact for fact in facts if fact.entity_type.value == "PROFESSOR"]
            contacts = uow.professor_contacts.for_professor(professor_id, limit=50)
            publications = uow.publications.for_professor(professor_id, limit=publication_limit)
            plans = uow.study_plans.for_professor(professor_id, limit=5)
            emails = uow.email_records.for_professor(professor_id, limit=5)
            attempts = uow.contact_attempts.for_professor(professor_id, limit=5)
            source_ids = list(
                dict.fromkeys(
                    [fact.source_id for fact in facts]
                    + [contact.source_id for contact in contacts if contact.source_id]
                    + [
                        publication.source_id
                        for publication in publications
                        if publication.source_id
                    ]
                )
            )[:source_limit]
            sources = [
                source
                for source_id in source_ids
                if (source := uow.sources.get(source_id)) is not None
            ]
            dates = [date for date in (professor.last_verified_at, _verified_at(facts)) if date]
            return {
                "professor": asdict(professor),
                "university": {"id": university.id, "canonical_name": university.canonical_name},
                "verified_contacts": [asdict(item) for item in contacts if item.verified],
                "other_contacts": [asdict(item) for item in contacts if not item.verified][:10],
                "facts": [asdict(item) for item in facts],
                "recent_publications": [asdict(item) for item in publications],
                "sources": [asdict(item) for item in sources],
                "study_plans": [asdict(item) for item in plans],
                "outreach": {
                    "emails": [asdict(item) for item in emails],
                    "attempts": [asdict(item) for item in attempts],
                },
                "last_verified_at": max(dates) if dates else None,
            }

    def university(
        self,
        university_id: UUID,
        *,
        professor_limit: int = 20,
        program_limit: int = 20,
        source_limit: int = 10,
    ) -> dict[str, object]:
        _limit(professor_limit, 50)
        _limit(program_limit, 50)
        _limit(source_limit, 50)
        with self._uow() as uow:
            university = uow.universities.get(university_id)
            if university is None:
                raise NotFoundError("University does not exist")
            programs = uow.programs.for_university(university_id, limit=program_limit)
            professors = uow.professors.for_university(university_id, limit=professor_limit)
            facts = [
                fact
                for fact in uow.research_facts.for_entity(university_id, limit=30)
                if fact.entity_type.value == "UNIVERSITY"
            ]
            source_ids = list(dict.fromkeys(fact.source_id for fact in facts))[:source_limit]
            sources = [
                source
                for source_id in source_ids
                if (source := uow.sources.get(source_id)) is not None
            ]
            dates = [
                date
                for date in [_verified_at(facts)]
                + [program.last_verified_at for program in programs]
                if date
            ]
            return {
                "university": asdict(university),
                "programs": [asdict(item) for item in programs],
                "admission_facts": [asdict(item) for item in facts],
                "professors": [
                    {
                        "id": item.id,
                        "name_en": item.name_en,
                        "name_zh": item.name_zh,
                        "department": item.department,
                        "status": item.status,
                        "last_verified_at": item.last_verified_at,
                    }
                    for item in professors
                ],
                "sources": [asdict(item) for item in sources],
                "last_verified_at": max(dates) if dates else None,
            }

    def professor_sources(self, professor_id: UUID, *, limit: int = 20) -> list[Source]:
        _limit(limit, 50)
        with self._uow() as uow:
            if uow.professors.get(professor_id) is None:
                raise NotFoundError("Professor does not exist")
            facts = uow.research_facts.for_entity(professor_id, limit=100)
            contacts = uow.professor_contacts.for_professor(professor_id, limit=100)
            publications = uow.publications.for_professor(professor_id, limit=100)
            ids = list(
                dict.fromkeys(
                    [fact.source_id for fact in facts]
                    + [contact.source_id for contact in contacts if contact.source_id]
                    + [
                        publication.source_id
                        for publication in publications
                        if publication.source_id
                    ]
                )
            )[:limit]
            return [source for source_id in ids if (source := uow.sources.get(source_id))]

    def stale_professors(self, days: int, *, limit: int = 100) -> list[dict[str, object]]:
        if not 1 <= days <= 3650:
            raise ValidationError("Days must be 1..3650")
        _limit(limit, 500)
        cutoff = utc_now() - timedelta(days=days)
        with self._uow() as uow:
            result: list[dict[str, object]] = []
            offset = 0
            while len(result) < limit:
                professors = uow.professors.list(limit=500, offset=offset)
                if not professors:
                    break
                for item in professors:
                    facts = uow.research_facts.for_entity(item.id, limit=100)
                    dates = [date for date in (item.last_verified_at, _verified_at(facts)) if date]
                    latest = max(dates) if dates else None
                    if latest is None or latest < cutoff:
                        result.append(
                            {"id": item.id, "name_en": item.name_en, "last_verified_at": latest}
                        )
                    if len(result) >= limit:
                        break
                offset += len(professors)
            return result

    def stale_universities(self, days: int, *, limit: int = 100) -> list[dict[str, object]]:
        if not 1 <= days <= 3650:
            raise ValidationError("Days must be 1..3650")
        _limit(limit, 500)
        cutoff = utc_now() - timedelta(days=days)
        with self._uow() as uow:
            result: list[dict[str, object]] = []
            offset = 0
            while len(result) < limit:
                universities = uow.universities.list(limit=500, offset=offset)
                if not universities:
                    break
                for item in universities:
                    facts = uow.research_facts.for_entity(item.id, limit=100)
                    programs = uow.programs.for_university(item.id, limit=100)
                    dates = [
                        date
                        for date in [_verified_at(facts)]
                        + [program.last_verified_at for program in programs]
                        if date
                    ]
                    latest = max(dates) if dates else None
                    if latest is None or latest < cutoff:
                        result.append(
                            {
                                "id": item.id,
                                "canonical_name": item.canonical_name,
                                "last_verified_at": latest,
                            }
                        )
                    if len(result) >= limit:
                        break
                offset += len(universities)
            return result
