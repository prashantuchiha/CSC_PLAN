from datetime import datetime
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import ContactType

from .base import Base, UTCDateTime


class ContactAttemptRow(Base):
    __tablename__ = "contact_attempts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    professor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("professors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    channel: Mapped[ContactType] = mapped_column(
        Enum(
            ContactType, native_enum=False, create_constraint=True, name="contact_attempts_channel"
        ),
        nullable=False,
    )
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    email_record_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("email_records.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
