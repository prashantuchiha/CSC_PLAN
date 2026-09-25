import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from china_masters.bootstrap import Container
from china_masters.domain.exceptions import (
    ConflictError,
    DomainError,
    NotFoundError,
)
from china_masters.infrastructure.configuration.settings import Settings
from china_masters.infrastructure.logging.setup import configure_logging
from china_masters.interfaces.api.routers import evidence, jobs, professors, universities


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(configuration.log_level, configuration.log_json)
        app.state.container = Container(configuration)
        try:
            yield
        finally:
            app.state.container.close()

    app = FastAPI(title="China Masters Research OS", version="0.3.0", lifespan=lifespan)

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        code = (
            404
            if isinstance(exc, NotFoundError)
            else 409
            if isinstance(exc, ConflictError)
            else 422
        )
        return JSONResponse(
            status_code=code, content={"detail": str(exc), "type": type(exc).__name__}
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logging.getLogger(__name__).error("Unhandled request failure", exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "phase": "3"}

    for router in (universities.router, professors.router, evidence.router, jobs.router):
        app.include_router(router)
    return app
