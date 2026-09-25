from contextlib import AbstractContextManager

from china_masters.application.commands.jobs import CreateJobs
from china_masters.application.services.jobs import JobService
from china_masters.application.services.universities import UniversityService
from china_masters.domain.entities import Professor, University
from china_masters.domain.enums import JobType


class MemoryRepository:
    def __init__(self, items=()):
        self.items = {item.id: item for item in items}

    def add(self, entity):
        self.items[entity.id] = entity

    def get(self, entity_id):
        return self.items.get(entity_id)

    def list(self, *, limit=100, offset=0):
        return list(self.items.values())[offset : offset + limit]


class MemoryUnitOfWork(AbstractContextManager):
    def __init__(self):
        for name in (
            "universities",
            "programs",
            "professors",
            "professor_contacts",
            "sources",
            "research_facts",
            "publications",
            "study_plans",
            "email_records",
            "contact_attempts",
            "research_jobs",
        ):
            setattr(self, name, MemoryRepository())
        self.commits = 0

    def __exit__(self, *args):
        pass

    def commit(self):
        self.commits += 1


def test_services_accept_non_sqlalchemy_ports():
    uow = MemoryUnitOfWork()
    universities = UniversityService(lambda: uow)
    university = universities.create(University(canonical_name="In memory"))
    assert universities.get(university.id) == university
    professor = Professor(university_id=university.id, name_en="Fixture")
    uow.professors.add(professor)
    jobs = JobService(lambda: uow).create(
        CreateJobs(job_type=JobType.PROFESSOR_RESEARCH, entity_ids=(professor.id,))
    )
    assert len(jobs) == 1
    assert uow.commits == 2
