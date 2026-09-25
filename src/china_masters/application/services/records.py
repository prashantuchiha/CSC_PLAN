"""Focused workflows for the remaining research and outreach records."""

from dataclasses import replace
from uuid import UUID

from china_masters.application.ports.unit_of_work import UnitOfWorkFactory
from china_masters.application.services.normalization import normalized_doi, normalized_title
from china_masters.application.services.references import require_reference
from china_masters.domain.entities import (
    ContactAttempt,
    EmailRecord,
    ProfessorContact,
    Program,
    Publication,
    StudyPlan,
)
from china_masters.domain.enums import EntityType
from china_masters.domain.exceptions import NotFoundError, ReferenceError, ValidationError
from china_masters.domain.value_objects import utc_now


class ProgramService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def create(self, program: Program) -> Program:
        with self._uow() as uow:
            require_reference(uow, EntityType.UNIVERSITY, program.university_id)
            uow.programs.add(program)
            uow.commit()
        return program

    def get(self, program_id: UUID) -> Program:
        with self._uow() as uow:
            result = uow.programs.get(program_id)
            if result is None:
                raise NotFoundError(f"Program {program_id} does not exist")
            return result

    def for_university(self, university_id: UUID, *, limit: int = 100) -> list[Program]:
        with self._uow() as uow:
            require_reference(uow, EntityType.UNIVERSITY, university_id)
            return uow.programs.for_university(university_id, limit=limit)

    def update(self, program: Program) -> Program:
        with self._uow() as uow:
            existing = uow.programs.get(program.id)
            if existing is None:
                raise NotFoundError(f"Program {program.id} does not exist")
            if existing.university_id != program.university_id:
                raise ValidationError("Program university cannot be changed")
            uow.programs.save(program)
            uow.commit()
        return program


class ProfessorContactService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def add(self, contact: ProfessorContact) -> ProfessorContact:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, contact.professor_id)
            if contact.source_id is not None:
                require_reference(uow, EntityType.SOURCE, contact.source_id)
            for existing in uow.professor_contacts.for_professor(contact.professor_id, limit=10000):
                if (existing.contact_type, existing.value.casefold()) == (
                    contact.contact_type,
                    contact.value.casefold(),
                ):
                    if contact.verified and not existing.verified:
                        updated = replace(
                            existing,
                            verified=True,
                            source_id=contact.source_id,
                            notes=contact.notes or existing.notes,
                        )
                        uow.professor_contacts.save(updated)
                        uow.commit()
                        return updated
                    return existing
            uow.professor_contacts.add(contact)
            uow.commit()
        return contact

    def for_professor(self, professor_id: UUID, *, limit: int = 100) -> list[ProfessorContact]:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, professor_id)
            return uow.professor_contacts.for_professor(professor_id, limit=limit)


class PublicationService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def add(self, publication: Publication) -> Publication:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, publication.professor_id)
            if publication.source_id is not None:
                require_reference(uow, EntityType.SOURCE, publication.source_id)
            for existing in uow.publications.for_professor(publication.professor_id, limit=10000):
                same_doi = bool(
                    publication.doi
                    and existing.doi
                    and normalized_doi(publication.doi) == normalized_doi(existing.doi)
                )
                same_title = existing.year == publication.year and normalized_title(
                    existing.title
                ) == normalized_title(publication.title)
                if same_doi or same_title:
                    return existing
            uow.publications.add(publication)
            uow.commit()
        return publication

    def for_professor(self, professor_id: UUID, *, limit: int = 20) -> list[Publication]:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, professor_id)
            return uow.publications.for_professor(professor_id, limit=limit)


class StudyPlanService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def create(self, plan: StudyPlan) -> StudyPlan:
        if plan.professor_id is None and plan.university_id is None:
            raise ValidationError("Study plan needs a professor or university")
        with self._uow() as uow:
            if plan.professor_id is not None:
                require_reference(uow, EntityType.PROFESSOR, plan.professor_id)
                professor = uow.professors.get(plan.professor_id)
                assert professor is not None
                if plan.university_id is not None and professor.university_id != plan.university_id:
                    raise ValidationError("Study plan professor and university differ")
            if plan.university_id is not None:
                require_reference(uow, EntityType.UNIVERSITY, plan.university_id)
            uow.study_plans.add(plan)
            uow.commit()
        return plan

    def for_professor(self, professor_id: UUID, *, limit: int = 20) -> list[StudyPlan]:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, professor_id)
            return uow.study_plans.for_professor(professor_id, limit=limit)

    def update(self, plan: StudyPlan) -> StudyPlan:
        with self._uow() as uow:
            existing = uow.study_plans.get(plan.id)
            if existing is None:
                raise NotFoundError(f"Study plan {plan.id} does not exist")
            if (existing.professor_id, existing.university_id) != (
                plan.professor_id,
                plan.university_id,
            ):
                raise ValidationError("Study plan owner cannot be changed")
            plan = replace(plan, updated_at=utc_now())
            uow.study_plans.save(plan)
            uow.commit()
        return plan


class EmailRecordService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def create(self, record: EmailRecord) -> EmailRecord:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, record.professor_id)
            uow.email_records.add(record)
            uow.commit()
        return record

    def for_professor(self, professor_id: UUID, *, limit: int = 20) -> list[EmailRecord]:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, professor_id)
            return uow.email_records.for_professor(professor_id, limit=limit)

    def update(self, record: EmailRecord) -> EmailRecord:
        with self._uow() as uow:
            existing = uow.email_records.get(record.id)
            if existing is None:
                raise NotFoundError(f"Email record {record.id} does not exist")
            if existing.professor_id != record.professor_id:
                raise ValidationError("Email record owner cannot be changed")
            record = replace(record, updated_at=utc_now())
            uow.email_records.save(record)
            uow.commit()
        return record


class ContactAttemptService:
    def __init__(self, uow: UnitOfWorkFactory) -> None:
        self._uow = uow

    def create(self, attempt: ContactAttempt) -> ContactAttempt:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, attempt.professor_id)
            if attempt.email_record_id is not None:
                email = uow.email_records.get(attempt.email_record_id)
                if email is None:
                    raise ReferenceError("Email record does not exist")
                if email.professor_id != attempt.professor_id:
                    raise ValidationError("Contact attempt email belongs to another professor")
            uow.contact_attempts.add(attempt)
            uow.commit()
        return attempt

    def for_professor(self, professor_id: UUID, *, limit: int = 20) -> list[ContactAttempt]:
        with self._uow() as uow:
            require_reference(uow, EntityType.PROFESSOR, professor_id)
            return uow.contact_attempts.for_professor(professor_id, limit=limit)
