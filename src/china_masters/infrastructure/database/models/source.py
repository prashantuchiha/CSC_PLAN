from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import SourceType

from .base import Base, UTCDateTime


class SourceRow(Base):
    __tablename__ = "sources"
    __table_args__ = (Index("ix_sources_normalized_url", "normalized_url", unique=True),)
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, native_enum=False, create_constraint=True, name="sources_source_type"),
        nullable=False,
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
