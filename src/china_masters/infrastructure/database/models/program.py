from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Numeric,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import (
    DegreeLevel,
)

from .base import Base, UTCDateTime


class ProgramRow(Base):
    __tablename__ = "programs"
    __table_args__ = (
        CheckConstraint("duration_years IS NULL OR duration_years > 0", name="positive_duration"),
        CheckConstraint("tuition_cny IS NULL OR tuition_cny >= 0", name="nonnegative_tuition"),
    )
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    university_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("universities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    degree_level: Mapped[DegreeLevel] = mapped_column(
        Enum(DegreeLevel, native_enum=False, create_constraint=True, name="programs_degree_level"),
        nullable=False,
    )
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_years: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tuition_cny: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    application_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    csc_supported: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
