import uuid
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import Role, db_enum


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    mobile: Mapped[str] = mapped_column(String(15), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[Role] = mapped_column(db_enum(Role), default=Role.PASSENGER)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
