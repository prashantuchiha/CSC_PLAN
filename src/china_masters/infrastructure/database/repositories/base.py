from copy import deepcopy
from dataclasses import fields
from typing import TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from china_masters.domain.entities.base import Entity
from china_masters.domain.exceptions import ConflictError, NotFoundError, ReferenceError
from china_masters.infrastructure.database.models import Base

T = TypeVar("T", bound=Entity)
M = TypeVar("M", bound=Base)


def translate_integrity(error: IntegrityError) -> None:
    if "FOREIGN KEY" in str(error.orig).upper():
        raise ReferenceError("A referenced record does not exist") from error
    raise ConflictError("Database constraint violated (duplicate ID or invalid value)") from error


class SQLAlchemyRepository[T: Entity, M: Base]:
    def __init__(self, session: Session, entity_type: type[T], model: type[M]) -> None:
        self.session, self.entity_type, self.model = session, entity_type, model

    def _entity(self, row: M) -> T:
        return self.entity_type(
            **{f.name: deepcopy(getattr(row, f.name)) for f in fields(self.entity_type)}
        )

    def add(self, entity: T) -> None:
        self.session.add(
            self.model(**{f.name: deepcopy(getattr(entity, f.name)) for f in fields(entity)})
        )
        self._flush()

    def _flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as error:
            translate_integrity(error)

    def get(self, entity_id: UUID) -> T | None:
        row = self.session.get(self.model, entity_id)
        return self._entity(row) if row is not None else None

    def list(self, *, limit: int = 100, offset: int = 0) -> list[T]:
        from china_masters.application.queries.pagination import Page

        Page(limit, offset)
        rows = self.session.scalars(
            select(self.model).order_by(self.model.id).limit(limit).offset(offset)
        )
        return [self._entity(row) for row in rows]

    def save(self, entity: T) -> None:
        values = {
            f.name: deepcopy(getattr(entity, f.name)) for f in fields(entity) if f.name != "id"
        }
        row = self.session.get(self.model, entity.id)
        if row is None:
            raise NotFoundError(f"{self.entity_type.__name__} {entity.id} does not exist")
        for key, value in values.items():
            setattr(row, key, value)
        self._flush()
