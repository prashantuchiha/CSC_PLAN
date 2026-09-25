from uuid import UUID

from fastapi import APIRouter

from china_masters.domain.entities import Program, University
from china_masters.interfaces.api.dependencies import (
    ContextDep,
    PageDep,
    ProfessorDep,
    ProgramDep,
    UniversityDep,
    WorkspaceDep,
)
from china_masters.interfaces.api.schemas import (
    ProfessorResponse,
    ProgramCreate,
    UniversityCreate,
    UniversityResponse,
    WorkspaceResponse,
)

router = APIRouter(prefix="/universities", tags=["universities"])


@router.get("/{university_id}/programs")
def list_programs(university_id: UUID, service: ProgramDep, limit: int = 20) -> object:
    return service.for_university(university_id, limit=limit)


@router.post("/{university_id}/programs", status_code=201)
def create_program(university_id: UUID, body: ProgramCreate, service: ProgramDep) -> object:
    return service.create(Program(university_id=university_id, **body.model_dump()))


@router.get("/{university_id}/context")
def get_context(
    university_id: UUID,
    service: ContextDep,
    professor_limit: int = 20,
    program_limit: int = 20,
    source_limit: int = 10,
) -> object:
    return service.university(
        university_id,
        professor_limit=professor_limit,
        program_limit=program_limit,
        source_limit=source_limit,
    )


@router.get("", response_model=list[UniversityResponse])
def list_universities(service: UniversityDep, page: PageDep) -> object:
    return service.list(page)


@router.post("", response_model=UniversityResponse, status_code=201)
def create_university(body: UniversityCreate, service: UniversityDep) -> object:
    return service.create(University(**body.model_dump()))


@router.get("/{university_id}", response_model=UniversityResponse)
def get_university(university_id: UUID, service: UniversityDep) -> object:
    return service.get(university_id)


@router.get("/{university_id}/professors", response_model=list[ProfessorResponse])
def list_professors(university_id: UUID, service: ProfessorDep, page: PageDep) -> object:
    return service.list(page, university_id=university_id)


@router.post("/{university_id}/workspace", response_model=WorkspaceResponse)
def create_workspace(university_id: UUID, service: WorkspaceDep) -> WorkspaceResponse:
    return WorkspaceResponse(relative_path=service.for_university(university_id))
