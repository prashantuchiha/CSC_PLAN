from uuid import UUID

from fastapi import APIRouter

from china_masters.domain.entities import ResearchFact, Source
from china_masters.interfaces.api.dependencies import EvidenceDep, PageDep
from china_masters.interfaces.api.schemas import (
    ResearchFactCreate,
    ResearchFactResponse,
    SourceCreate,
    SourceResponse,
)

router = APIRouter(tags=["evidence"])


@router.post("/sources", response_model=SourceResponse, status_code=201)
def add_source(body: SourceCreate, service: EvidenceDep) -> object:
    return service.add_source(Source(**body.model_dump(exclude_none=True)))


@router.get("/sources/{source_id}", response_model=SourceResponse)
def get_source(source_id: UUID, service: EvidenceDep) -> object:
    return service.get_source(source_id)


@router.post("/research-facts", response_model=ResearchFactResponse, status_code=201)
def add_fact(body: ResearchFactCreate, service: EvidenceDep) -> object:
    return service.add_fact(ResearchFact(**body.model_dump()))


@router.get("/research-facts", response_model=list[ResearchFactResponse])
def list_facts(service: EvidenceDep, page: PageDep) -> object:
    return service.list_facts(page)
