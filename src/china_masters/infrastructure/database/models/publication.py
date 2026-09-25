from uuid import UUID

from sqlalchemy import ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class PublicationRow(Base):
    __tablename__ = "publications"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    professor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("professors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(Text, nullable=True)
    doi: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=True
    )
