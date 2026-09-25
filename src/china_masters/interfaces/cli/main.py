import json
import signal
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from threading import Event
from typing import Annotated
from uuid import UUID

import typer

from china_masters.application.commands.jobs import CreateJobs
from china_masters.application.queries.pagination import Page
from china_masters.bootstrap import Container
from china_masters.domain.entities import Professor, University
from china_masters.domain.enums import JobStatus, JobType
from china_masters.domain.exceptions import DomainError
from china_masters.infrastructure.configuration.settings import Settings
from china_masters.infrastructure.logging.setup import configure_logging

app = typer.Typer(no_args_is_help=True)
university_app = typer.Typer(no_args_is_help=True)
professor_app = typer.Typer(no_args_is_help=True)
job_app = typer.Typer(no_args_is_help=True)
worker_app = typer.Typer(no_args_is_help=True)
mcp_app = typer.Typer(no_args_is_help=True)
app.add_typer(university_app, name="university")
app.add_typer(professor_app, name="professor")
app.add_typer(job_app, name="job")
app.add_typer(worker_app, name="worker")
app.add_typer(mcp_app, name="mcp")


def emit(value: object) -> None:
    def encode(item: object) -> object:
        if is_dataclass(item) and not isinstance(item, type):
            values = asdict(item)
            values.pop("claim_token", None)
            return values
        return str(item)

    typer.echo(json.dumps(value, default=encode, indent=2, ensure_ascii=False))


@contextmanager
def services() -> Iterator[Container]:
    settings = Settings()
    configure_logging(settings.log_level, settings.log_json)
    container = Container(settings)
    try:
        yield container
    except DomainError as exc:
        typer.echo(f"{type(exc).__name__}: {exc}", err=True)
        raise typer.Exit(1) from exc
    finally:
        container.close()


@app.command()
def health() -> None:
    """Process liveness; query a list command to check a migrated database."""
    emit({"status": "ok", "phase": "3"})


@mcp_app.command("run")
def mcp_run() -> None:
    """Run the independent local stdio MCP server."""
    from china_masters.interfaces.mcp.server import create_server

    with services() as container:
        create_server(container).run(transport="stdio")


@professor_app.command("context")
def professor_context(
    professor_id: UUID, publication_limit: int = 10, source_limit: int = 10
) -> None:
    with services() as container:
        emit(
            container.context.professor(
                professor_id, publication_limit=publication_limit, source_limit=source_limit
            )
        )


@professor_app.command("contacts")
def professor_contacts(professor_id: UUID) -> None:
    with services() as container:
        emit(container.contacts.for_professor(professor_id))


@professor_app.command("publications")
def professor_publications(professor_id: UUID, limit: int = 20) -> None:
    with services() as container:
        emit(container.publications.for_professor(professor_id, limit=limit))


@university_app.command("context")
def university_context(university_id: UUID) -> None:
    with services() as container:
        emit(container.context.university(university_id))


@university_app.command("list")
def list_universities(limit: int = 100, offset: int = 0) -> None:
    with services() as container:
        emit(container.universities.list(Page(limit, offset)))


@university_app.command("create")
def create_university(name: str) -> None:
    with services() as container:
        emit(container.universities.create(University(canonical_name=name)))


@university_app.command("get")
def get_university(university_id: UUID) -> None:
    with services() as container:
        emit(container.universities.get(university_id))


@professor_app.command("list")
def list_professors(university_id: UUID | None = None, limit: int = 100, offset: int = 0) -> None:
    with services() as container:
        emit(container.professors.list(Page(limit, offset), university_id=university_id))


@professor_app.command("create")
def create_professor(university_id: UUID, name: str) -> None:
    with services() as container:
        emit(container.professors.create(Professor(university_id=university_id, name_en=name)))


@professor_app.command("workspace")
def professor_workspace(professor_id: UUID) -> None:
    with services() as container:
        emit({"relative_path": container.workspaces.for_professor(professor_id)})


@job_app.command("list")
def list_jobs(status: JobStatus | None = None, limit: int = 100, offset: int = 0) -> None:
    with services() as container:
        emit(container.jobs.list(Page(limit, offset), status=status))


@job_app.command("create")
def create_jobs(
    job_type: JobType,
    entity_id: Annotated[list[UUID] | None, typer.Option()] = None,
    payload_json: Annotated[str, typer.Option()] = "{}",
) -> None:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter("payload-json must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise typer.BadParameter("payload-json must be a JSON object")
    with services() as container:
        emit(
            container.jobs.create(
                CreateJobs(job_type=job_type, entity_ids=tuple(entity_id or []), payload=payload)
            )
        )


@job_app.command("get")
def get_job(job_id: UUID) -> None:
    with services() as container:
        emit(container.jobs.get(job_id))


@job_app.command("cancel")
def cancel_job(job_id: UUID) -> None:
    with services() as container:
        emit(container.jobs.cancel(job_id))


@job_app.command("resume")
def resume_job(job_id: UUID) -> None:
    with services() as container:
        emit(container.jobs.resume(job_id))


@job_app.command("transition")
def transition_job(job_id: UUID, status: JobStatus, error: str | None = None) -> None:
    with services() as container:
        emit(container.jobs.transition(job_id, status, error=error))


@worker_app.command("once")
def worker_once() -> None:
    """Recover leases, claim at most one eligible job, execute it, then exit."""
    with services() as container:
        result = container.create_worker().once()
        emit(result if result is not None else {"processed": False})


@worker_app.command("recover")
def worker_recover() -> None:
    """Recover expired leases without claiming another job."""
    with services() as container:
        emit(container.job_execution.recover_expired())


@worker_app.command("run")
def worker_run() -> None:
    """Poll the SQLite queue until Ctrl+C or SIGTERM."""
    stop = Event()
    signals = (signal.SIGINT, signal.SIGTERM)
    previous = {item: signal.getsignal(item) for item in signals}
    for item in signals:
        signal.signal(item, lambda signum, frame: stop.set())
    try:
        with services() as container:
            container.create_worker().run(stop)
    finally:
        for item, handler in previous.items():
            signal.signal(item, handler)


if __name__ == "__main__":
    app()
