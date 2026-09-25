from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import StudyPlanStatus

from .base import Base, UTCDateTime


class StudyPlanRow(Base):
    __tablename__ = "study_plans"
    __table_args__ = (CheckConstraint("version > 0", name="positive_version"),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    professor_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("professors.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    university_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("universities.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StudyPlanStatus] = mapped_column(
        Enum(StudyPlanStatus, native_enum=False, create_constraint=True, name="study_plans_status"),
        nullable=False,
    )
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
