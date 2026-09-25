from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import EmailStatus

from .base import Base, UTCDateTime


class EmailRecordRow(Base):
    __tablename__ = "email_records"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    professor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("professors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_thread_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EmailStatus] = mapped_column(
        Enum(EmailStatus, native_enum=False, create_constraint=True, name="email_records_status"),
        nullable=False,
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
