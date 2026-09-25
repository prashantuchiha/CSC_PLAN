from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, CheckConstraint, Enum, Index, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import EntityType, JobStatus, JobType
from china_masters.domain.value_objects import JSONValue

from .base import Base, UTCDateTime


class ResearchJobRow(Base):
    __tablename__ = "research_jobs"
    __table_args__ = (
        CheckConstraint("priority >= 0 AND priority <= 100", name="priority_range"),
        CheckConstraint("attempts >= 0 AND revision >= 0", name="counters_nonnegative"),
        CheckConstraint("(entity_id IS NULL) = (entity_type IS NULL)", name="target_pair"),
        CheckConstraint(
            "(status = 'RUNNING') = (worker_id IS NOT NULL AND claim_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL)",
            name="running_lease",
        ),
        Index("ix_research_jobs_queue", "status", "priority", "created_at"),
        Index("ix_research_jobs_lease", "status", "lease_expires_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    job_type: Mapped[JobType] = mapped_column(
        Enum(JobType, native_enum=False, create_constraint=True, name="research_jobs_job_type"),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, create_constraint=True, name="research_jobs_status"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[EntityType | None] = mapped_column(
        Enum(
            EntityType, native_enum=False, create_constraint=True, name="research_jobs_entity_type"
        ),
        nullable=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    payload_json: Mapped[dict[str, JSONValue]] = mapped_column(
        JSON(none_as_null=False), nullable=False
    )
    result_json: Mapped[dict[str, JSONValue] | None] = mapped_column(
        JSON(none_as_null=False), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_token: Mapped[UUID | None] = mapped_column(Uuid, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
