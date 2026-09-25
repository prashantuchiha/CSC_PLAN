from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import ProfessorStatus

from .base import Base, UTCDateTime


class ProfessorRow(Base):
    __tablename__ = "professors"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    university_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("universities.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    name_en: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_zh: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ProfessorStatus] = mapped_column(
        Enum(ProfessorStatus, native_enum=False, create_constraint=True, name="professors_status"),
        nullable=False,
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
