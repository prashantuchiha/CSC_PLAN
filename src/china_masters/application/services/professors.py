from __future__ import annotations

import builtins
from dataclasses import replace
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.application.queries.pagination import Page
from china_masters.application.services.references import require_reference
from china_masters.domain.entities import Professor
from china_masters.domain.enums import EntityType
from china_masters.domain.exceptions import NotFoundError, ValidationError
from china_masters.domain.value_objects import utc_now


class ProfessorService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def create(self, professor: Professor) -> Professor:
        with self._uow() as uow:
            require_reference(uow, EntityType.UNIVERSITY, professor.university_id)
            uow.professors.add(professor)
            uow.commit()
        return professor

    def get(self, professor_id: UUID) -> Professor:
        with self._uow() as uow:
            professor = uow.professors.get(professor_id)
            if professor is None:
                raise NotFoundError(f"Professor {professor_id} does not exist")
            return professor

    def list(self, page: Page = Page(), *, university_id: UUID | None = None) -> list[Professor]:
        with self._uow() as uow:
            if university_id is not None:
                require_reference(uow, EntityType.UNIVERSITY, university_id)
                return uow.professors.for_university(
                    university_id, limit=page.limit, offset=page.offset
                )
            return uow.professors.list(limit=page.limit, offset=page.offset)

    def update(self, professor: Professor) -> Professor:
        with self._uow() as uow:
            existing = uow.professors.get(professor.id)
            if existing is None:
                raise NotFoundError(f"Professor {professor.id} does not exist")
            if existing.university_id != professor.university_id:
                raise ValidationError("Professor university cannot be changed")
            professor = replace(professor, updated_at=utc_now())
            uow.professors.save(professor)
            uow.commit()
        return professor

    def search(
        self, query: str, *, university_id: UUID | None = None, limit: int = 20
    ) -> builtins.list[Professor]:
        needle = query.casefold().strip()
        if not needle or not 1 <= limit <= 100:
            raise ValidationError("Search requires a query and limit 1..100")
        with self._uow() as uow:
            found: builtins.list[Professor] = []
            offset = 0
            while len(found) < limit:
                professors = (
                    uow.professors.for_university(university_id, limit=500, offset=offset)
                    if university_id
                    else uow.professors.list(limit=500, offset=offset)
                )
                if not professors:
                    break
                for professor in professors:
                    text = " ".join(
                        filter(
                            None,
                            (
                                professor.name_en,
                                professor.name_zh,
                                professor.department,
                                professor.official_profile_url,
                            ),
                        )
                    ).casefold()
                    contacts = uow.professor_contacts.for_professor(professor.id, limit=100)
                    if needle in text or any(needle in item.value.casefold() for item in contacts):
                        found.append(professor)
                    if len(found) >= limit:
                        break
                offset += len(professors)
            return found[:limit]
