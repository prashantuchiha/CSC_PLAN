"""Sample handlers; replace with focused handlers in later phases."""

from china_masters.application.dto.job_execution import JobExecutionContext, JobExecutionResult
from china_masters.application.dto.job_payloads import (
    general_payload,
    professor_payload,
    university_payload,
)
from china_masters.application.ports.integrations import ResearchResult
from china_masters.application.ports.research_provider import ResearchProvider
from china_masters.application.services.professors import ProfessorService
from china_masters.application.services.universities import UniversityService
from china_masters.domain.entities import ResearchJob
from china_masters.domain.enums import JobType
from china_masters.domain.exceptions import ValidationError
from china_masters.domain.value_objects import JSONValue


def _candidate_result(research: ResearchResult, *, review: bool) -> JobExecutionResult:
    # Candidate facts stay in the job result; synthetic sources never become verified evidence.
    return JobExecutionResult(
        data={
            "synthetic": True,
            "candidate_facts": [
                {
                    "entity_type": fact.entity_type.value,
                    "entity_id": str(fact.entity_id),
                    "field_name": fact.field_name,
                    "value": fact.value,
                    "source_url": research.sources[0].url,
                }
                for fact in research.facts
            ],
        },
        review_required=review,
        message="Synthetic result; no external research performed",
    )


class ProfessorResearchJobHandler:
    job_type = JobType.PROFESSOR_RESEARCH

    def __init__(self, professors: ProfessorService, provider: ResearchProvider) -> None:
        self.professors = professors
        self.provider = provider

    def execute(self, context: JobExecutionContext, job: ResearchJob) -> JobExecutionResult:
        context.heartbeat()
        payload = professor_payload(job.payload_json)
        if job.attempts <= payload.fail_until_attempt:
            raise RuntimeError("Synthetic transient professor research failure")
        if job.entity_id is None:
            raise ValidationError("Professor job has no target")
        return _candidate_result(
            self.provider.research_professor(self.professors.get(job.entity_id)),
            review=payload.review_required and not payload.review_approved,
        )


class UniversityResearchJobHandler:
    job_type = JobType.UNIVERSITY_RESEARCH

    def __init__(self, universities: UniversityService, provider: ResearchProvider) -> None:
        self.universities = universities
        self.provider = provider

    def execute(self, context: JobExecutionContext, job: ResearchJob) -> JobExecutionResult:
        context.heartbeat()
        payload = university_payload(job.payload_json)
        if job.attempts <= payload.fail_until_attempt:
            raise RuntimeError("Synthetic transient university research failure")
        if job.entity_id is None:
            raise ValidationError("University job has no target")
        return _candidate_result(
            self.provider.research_university(self.universities.get(job.entity_id)),
            review=payload.review_required and not payload.review_approved,
        )


class GeneralCSCResearchJobHandler:
    job_type = JobType.GENERAL_CSC_RESEARCH

    def execute(self, context: JobExecutionContext, job: ResearchJob) -> JobExecutionResult:
        context.heartbeat()
        payload = general_payload(job.payload_json)
        if job.attempts <= payload.fail_until_attempt:
            raise RuntimeError("Synthetic transient CSC research failure")
        data: dict[str, JSONValue] = {
            "synthetic": True,
            "summary": "Synthetic CSC research fixture",
            "topic": payload.topic,
        }
        return JobExecutionResult(
            data=data,
            review_required=payload.review_required and not payload.review_approved,
            message="Synthetic result; no external research performed",
        )
