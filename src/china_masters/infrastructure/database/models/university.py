from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, UTCDateTime


class UniversityRow(Base):
    __tablename__ = "universities"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    chinese_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    abbreviation: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    province: Mapped[str | None] = mapped_column(Text, nullable=True)
    official_website: Mapped[str | None] = mapped_column(Text, nullable=True)
    international_admissions_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
