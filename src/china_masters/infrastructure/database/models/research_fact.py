from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import EntityType, VerificationStatus
from china_masters.domain.value_objects import JSONValue

from .base import Base, UTCDateTime


class ResearchFactRow(Base):
    __tablename__ = "research_facts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(
            EntityType, native_enum=False, create_constraint=True, name="research_facts_entity_type"
        ),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[JSONValue] = mapped_column(JSON(none_as_null=False), nullable=False)
    source_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            native_enum=False,
            create_constraint=True,
            name="research_facts_verification_status",
        ),
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
