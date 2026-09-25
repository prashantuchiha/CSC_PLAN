from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from china_masters.domain.enums import ContactType

from .base import Base


class ProfessorContactRow(Base):
    __tablename__ = "professor_contacts"
    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    professor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("professors.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    contact_type: Mapped[ContactType] = mapped_column(
        Enum(
            ContactType,
            native_enum=False,
            create_constraint=True,
            name="professor_contacts_contact_type",
        ),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("sources.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
