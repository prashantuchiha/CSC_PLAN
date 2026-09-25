from typing import Protocol

from china_masters.application.dto.job_execution import JobExecutionContext, JobExecutionResult
from china_masters.domain.entities import ResearchJob
from china_masters.domain.enums import JobType


class JobHandler(Protocol):
    @property
    def job_type(self) -> JobType: ...

    def execute(self, context: JobExecutionContext, job: ResearchJob) -> JobExecutionResult: ...
