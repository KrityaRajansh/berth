import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import JobStatus, db_enum


class AuditEvent(Base):
    __tablename__ = "audit_event"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    actor_id: Mapped[uuid.UUID | None]
    event_type: Mapped[str] = mapped_column(String(40))
    entity: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[str] = mapped_column(String(40))
    data: Mapped[dict[str, Any]]
    created_at: Mapped[datetime]


class JobRun(Base):
    __tablename__ = "job_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(40))
    triggered_by: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime]
    finished_at: Mapped[datetime | None]
    status: Mapped[JobStatus] = mapped_column(db_enum(JobStatus))
    items_processed: Mapped[int] = mapped_column(default=0)
    detail: Mapped[str | None] = mapped_column(Text)


class LoginAttempt(Base):
    __tablename__ = "login_attempt"
    __table_args__ = (Index(None, "email", "attempted_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(254))
    succeeded: Mapped[bool]
    attempted_at: Mapped[datetime]
