from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWork
from china_masters.domain.entities.base import Entity
from china_masters.domain.enums import EntityType
from china_masters.domain.exceptions import ReferenceError
from china_masters.domain.repositories.base import Repository


def require_reference(uow: UnitOfWork, kind: EntityType, entity_id: UUID) -> Entity:
    repositories: dict[EntityType, Repository] = {
        EntityType.UNIVERSITY: uow.universities,
        EntityType.PROGRAM: uow.programs,
        EntityType.PROFESSOR: uow.professors,
        EntityType.SOURCE: uow.sources,
        EntityType.PROFESSOR_CONTACT: uow.professor_contacts,
        EntityType.PUBLICATION: uow.publications,
        EntityType.STUDY_PLAN: uow.study_plans,
        EntityType.EMAIL_RECORD: uow.email_records,
        EntityType.CONTACT_ATTEMPT: uow.contact_attempts,
    }
    entity = repositories[kind].get(entity_id)
    if entity is None:
        raise ReferenceError(f"{kind} {entity_id} does not exist")
    return entity
