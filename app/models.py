from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db

LABEL_MAX_LENGTH = 30


class Case(db.Model):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(LABEL_MAX_LENGTH), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    consultations: Mapped[list["Consultation"]] = relationship(
        back_populates="case", order_by="(Consultation.created_at, Consultation.id)"
    )


class Consultation(db.Model):
    __tablename__ = "consultations"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    parameters: Mapped[dict] = mapped_column(JSONB)
    derived: Mapped[dict] = mapped_column(JSONB)
    fired_rules: Mapped[list[str]] = mapped_column(ARRAY(String))
    rules_version: Mapped[str] = mapped_column(String(64))

    case: Mapped[Case] = relationship(back_populates="consultations")
