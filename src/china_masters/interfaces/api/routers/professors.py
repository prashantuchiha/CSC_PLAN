from uuid import UUID

from fastapi import APIRouter

from china_masters.domain.entities import Professor, ProfessorContact, Publication
from china_masters.interfaces.api.dependencies import (
    ContactDep,
    ContextDep,
    PageDep,
    ProfessorDep,
    PublicationDep,
    WorkspaceDep,
)
from china_masters.interfaces.api.schemas import (
    ContactCreate,
    ProfessorCreate,
    ProfessorResponse,
    PublicationCreate,
    WorkspaceResponse,
)

router = APIRouter(prefix="/professors", tags=["professors"])


@router.post("/{professor_id}/contacts", status_code=201)
def add_contact(professor_id: UUID, body: ContactCreate, service: ContactDep) -> object:
    return service.add(ProfessorContact(professor_id=professor_id, **body.model_dump()))


@router.post("/{professor_id}/publications", status_code=201)
def add_publication(professor_id: UUID, body: PublicationCreate, service: PublicationDep) -> object:
    return service.add(Publication(professor_id=professor_id, **body.model_dump()))


@router.get("/{professor_id}/context")
def get_context(
    professor_id: UUID, service: ContextDep, publication_limit: int = 10, source_limit: int = 10
) -> object:
    return service.professor(
        professor_id, publication_limit=publication_limit, source_limit=source_limit
    )


@router.get("/{professor_id}/contacts")
def get_contacts(professor_id: UUID, service: ContactDep) -> object:
    return service.for_professor(professor_id)


@router.get("/{professor_id}/publications")
def get_publications(professor_id: UUID, service: PublicationDep, limit: int = 20) -> object:
    return service.for_professor(professor_id, limit=limit)


@router.get("", response_model=list[ProfessorResponse])
def list_professors(service: ProfessorDep, page: PageDep) -> object:
    return service.list(page)


@router.post("", response_model=ProfessorResponse, status_code=201)
def create_professor(body: ProfessorCreate, service: ProfessorDep) -> object:
    return service.create(Professor(**body.model_dump()))


@router.get("/{professor_id}", response_model=ProfessorResponse)
def get_professor(professor_id: UUID, service: ProfessorDep) -> object:
    return service.get(professor_id)


@router.post("/{professor_id}/workspace", response_model=WorkspaceResponse)
def create_workspace(professor_id: UUID, service: WorkspaceDep) -> WorkspaceResponse:
    return WorkspaceResponse(relative_path=service.for_professor(professor_id))
