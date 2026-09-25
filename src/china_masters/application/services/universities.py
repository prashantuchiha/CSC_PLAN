from __future__ import annotations

import builtins
from dataclasses import replace
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.application.queries.pagination import Page
from china_masters.domain.entities import University
from china_masters.domain.exceptions import NotFoundError, ValidationError
from china_masters.domain.value_objects import utc_now


class UniversityService:
    def __init__(self, uow_factory: UnitOfWorkFactory) -> None:
        self._uow = uow_factory

    def create(self, university: University) -> University:
        with self._uow() as uow:
            uow.universities.add(university)
            uow.commit()
        return university

    def get(self, university_id: UUID) -> University:
        with self._uow() as uow:
            university = uow.universities.get(university_id)
            if university is None:
                raise NotFoundError(f"University {university_id} does not exist")
            return university

    def list(self, page: Page = Page()) -> list[University]:
        with self._uow() as uow:
            return uow.universities.list(limit=page.limit, offset=page.offset)

    def update(self, university: University) -> University:
        with self._uow() as uow:
            if uow.universities.get(university.id) is None:
                raise NotFoundError(f"University {university.id} does not exist")
            university = replace(university, updated_at=utc_now())
            uow.universities.save(university)
            uow.commit()
        return university

    def search(self, query: str, *, limit: int = 20) -> builtins.list[University]:
        needle = query.casefold().strip()
        if not needle or not 1 <= limit <= 100:
            raise ValidationError("Search requires a query and limit 1..100")
        with self._uow() as uow:
            found: builtins.list[University] = []
            offset = 0
            while len(found) < limit:
                items = uow.universities.list(limit=500, offset=offset)
                if not items:
                    break
                found.extend(
                    item
                    for item in items
                    if needle
                    in " ".join(
                        filter(
                            None,
                            (item.canonical_name, item.chinese_name, item.abbreviation, item.city),
                        )
                    ).casefold()
                )
                offset += len(items)
            return found[:limit]
