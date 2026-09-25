from uuid import UUID

from fastapi import APIRouter

from china_masters.application.commands.jobs import CreateJobs
from china_masters.domain.enums import JobStatus
from china_masters.interfaces.api.dependencies import JobDep, PageDep
from china_masters.interfaces.api.schemas import JobCreate, JobTransition, ResearchJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=list[ResearchJobResponse], status_code=201)
def create_jobs(body: JobCreate, service: JobDep) -> object:
    ids = tuple(body.entity_ids or ([body.entity_id] if body.entity_id else []))
    return service.create(
        CreateJobs(
            job_type=body.job_type,
            entity_type=body.entity_type,
            entity_ids=ids,
            priority=body.priority,
            payload=body.payload_json,
        )
    )


@router.get("", response_model=list[ResearchJobResponse])
def list_jobs(service: JobDep, page: PageDep, status: JobStatus | None = None) -> object:
    return service.list(page, status=status)


@router.get("/{job_id}", response_model=ResearchJobResponse)
def get_job(job_id: UUID, service: JobDep) -> object:
    return service.get(job_id)


@router.post("/{job_id}/cancel", response_model=ResearchJobResponse)
def cancel_job(job_id: UUID, service: JobDep) -> object:
    return service.cancel(job_id)


@router.post("/{job_id}/resume", response_model=ResearchJobResponse)
def resume_job(job_id: UUID, service: JobDep) -> object:
    return service.resume(job_id)


@router.post("/{job_id}/transition", response_model=ResearchJobResponse)
def transition_job(job_id: UUID, body: JobTransition, service: JobDep) -> object:
    return service.transition(
        job_id, body.status, result=body.result_json, error=body.error_message
    )
