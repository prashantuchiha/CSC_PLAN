from typing import Annotated

from fastapi import Depends, Query, Request

from china_masters.application.queries.pagination import Page
from china_masters.application.services.context import ResearchContextService
from china_masters.application.services.evidence import ResearchEvidenceService
from china_masters.application.services.jobs import JobService
from china_masters.application.services.professors import ProfessorService
from china_masters.application.services.records import (
    ProfessorContactService,
    ProgramService,
    PublicationService,
)
from china_masters.application.services.universities import UniversityService
from china_masters.application.services.workspaces import WorkspaceService
from china_masters.bootstrap import Container


def container(request: Request) -> Container:
    return request.app.state.container


def universities(c: Annotated[Container, Depends(container)]) -> UniversityService:
    return c.universities


def professors(c: Annotated[Container, Depends(container)]) -> ProfessorService:
    return c.professors


def evidence(c: Annotated[Container, Depends(container)]) -> ResearchEvidenceService:
    return c.evidence


def jobs(c: Annotated[Container, Depends(container)]) -> JobService:
    return c.jobs


def workspaces(c: Annotated[Container, Depends(container)]) -> WorkspaceService:
    return c.workspaces


def context(c: Annotated[Container, Depends(container)]) -> ResearchContextService:
    return c.context


def contacts(c: Annotated[Container, Depends(container)]) -> ProfessorContactService:
    return c.contacts


def publications(c: Annotated[Container, Depends(container)]) -> PublicationService:
    return c.publications


def programs(c: Annotated[Container, Depends(container)]) -> ProgramService:
    return c.programs


def pagination(
    limit: Annotated[int, Query(ge=1, le=500)] = 100, offset: Annotated[int, Query(ge=0)] = 0
) -> Page:
    return Page(limit, offset)


UniversityDep = Annotated[UniversityService, Depends(universities)]
ProfessorDep = Annotated[ProfessorService, Depends(professors)]
EvidenceDep = Annotated[ResearchEvidenceService, Depends(evidence)]
JobDep = Annotated[JobService, Depends(jobs)]
WorkspaceDep = Annotated[WorkspaceService, Depends(workspaces)]
PageDep = Annotated[Page, Depends(pagination)]
ContextDep = Annotated[ResearchContextService, Depends(context)]
ContactDep = Annotated[ProfessorContactService, Depends(contacts)]
PublicationDep = Annotated[PublicationService, Depends(publications)]
ProgramDep = Annotated[ProgramService, Depends(programs)]
