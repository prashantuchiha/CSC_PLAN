"""HTTP validation and serialization. Domain dataclasses remain framework-free."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    field_validator,
    model_validator,
)
from pydantic import JsonValue as JSONValue

from china_masters.domain.enums import (
    ContactType,
    DegreeLevel,
    EntityType,
    JobStatus,
    JobType,
    ProfessorStatus,
    SourceType,
    VerificationStatus,
)


class ProgramCreate(BaseModel):
    name: str = Field(min_length=1)
    degree_level: DegreeLevel = DegreeLevel.MASTERS
    department: str | None = None
    language: str | None = None
    duration_years: Decimal | None = None
    tuition_cny: Decimal | None = None
    application_deadline: date | None = None
    csc_supported: bool | None = None
    notes: str | None = None


class ContactCreate(BaseModel):
    contact_type: ContactType
    value: str = Field(min_length=1)
    source_id: UUID | None = None
    verified: bool = False
    notes: str | None = None


class PublicationCreate(BaseModel):
    title: str = Field(min_length=1)
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    source_id: UUID | None = None


class Input(BaseModel):
    model_config = ConfigDict(
        extra="forbid", str_strip_whitespace=True, str_min_length=1, allow_inf_nan=False
    )

    @field_validator("*", mode="after")
    @classmethod
    def validate_urls(cls, value: object, info: object) -> object:
        name = getattr(info, "field_name", "")
        if value is not None and (name.endswith("_url") or name in {"url", "official_website"}):
            TypeAdapter(HttpUrl).validate_python(value)
        return value


class Output(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UniversityCreate(Input):
    canonical_name: str
    chinese_name: str | None = None
    abbreviation: str | None = None
    city: str | None = None
    province: str | None = None
    official_website: str | None = None
    international_admissions_url: str | None = None
    notes: str | None = None


class UniversityResponse(Output):
    id: UUID
    canonical_name: str
    chinese_name: str | None
    abbreviation: str | None
    city: str | None
    province: str | None
    official_website: str | None
    international_admissions_url: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ProfessorCreate(Input):
    university_id: UUID
    name_en: str
    department: str | None = None
    name_zh: str | None = None
    title: str | None = None
    official_profile_url: str | None = None
    research_summary: str | None = None
    status: ProfessorStatus = ProfessorStatus.NEW


class ProfessorResponse(Output):
    id: UUID
    university_id: UUID
    name_en: str
    department: str | None
    name_zh: str | None
    title: str | None
    official_profile_url: str | None
    research_summary: str | None
    status: ProfessorStatus
    last_verified_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SourceCreate(Input):
    url: str
    source_type: SourceType
    title: str | None = None
    publisher: str | None = None
    domain: str | None = None
    retrieved_at: AwareDatetime | None = None
    published_at: AwareDatetime | None = None
    content_hash: str | None = None
    local_snapshot_path: str | None = None
    notes: str | None = None


class SourceResponse(Output):
    id: UUID
    url: str
    source_type: SourceType
    title: str | None
    publisher: str | None
    domain: str | None
    retrieved_at: datetime
    published_at: datetime | None
    content_hash: str | None
    local_snapshot_path: str | None
    notes: str | None


class ResearchFactCreate(Input):
    entity_type: EntityType
    entity_id: UUID
    field_name: str
    value: JSONValue
    source_id: UUID
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_at: AwareDatetime | None = None
    notes: str | None = None


class ResearchFactResponse(Output):
    id: UUID
    entity_type: EntityType
    entity_id: UUID
    field_name: str
    value: JSONValue
    source_id: UUID
    verification_status: VerificationStatus
    verified_at: datetime | None
    notes: str | None


class ResearchJobResponse(Output):
    id: UUID
    job_type: JobType
    status: JobStatus
    priority: int
    entity_type: EntityType | None
    entity_id: UUID | None
    payload_json: dict[str, JSONValue]
    result_json: dict[str, JSONValue] | None
    error_message: str | None
    attempts: int
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    worker_id: str | None
    lease_expires_at: datetime | None
    next_attempt_at: datetime | None
    revision: int


class JobCreate(Input):
    job_type: JobType
    entity_type: EntityType | None = None
    entity_id: UUID | None = None
    entity_ids: list[UUID] | None = Field(default=None, min_length=1, max_length=500)
    priority: int = Field(default=0, ge=0, le=100)
    payload_json: dict[str, JSONValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def exclusive_targets(self) -> "JobCreate":
        if self.entity_id is not None and self.entity_ids is not None:
            raise ValueError("Provide entity_id or entity_ids, not both")
        return self


class JobTransition(Input):
    status: JobStatus
    result_json: dict[str, JSONValue] | None = None
    error_message: str | None = None


class WorkspaceResponse(Output):
    relative_path: str
