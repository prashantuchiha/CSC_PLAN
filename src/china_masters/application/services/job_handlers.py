from china_masters.application.ports.job_handler import JobHandler
from china_masters.domain.enums import JobType
from china_masters.domain.exceptions import ValidationError


class UnsupportedJobError(ValidationError):
    pass


class JobHandlerRegistry:
    def __init__(self, handlers: tuple[JobHandler, ...]) -> None:
        self._handlers: dict[JobType, JobHandler] = {}
        for handler in handlers:
            if handler.job_type in self._handlers:
                raise ValidationError(f"Duplicate handler for {handler.job_type}")
            self._handlers[handler.job_type] = handler

    def get(self, job_type: JobType) -> JobHandler:
        try:
            return self._handlers[job_type]
        except KeyError as exc:
            raise UnsupportedJobError(f"No handler registered for {job_type}") from exc
