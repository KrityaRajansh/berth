from datetime import date, datetime
from typing import Any

from sqlalchemy import ForeignKey, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import RunStatus, TravelClass, db_enum
from app.models.network import Train


class TrainRun(Base):
    __tablename__ = "train_run"
    __table_args__ = (UniqueConstraint("train_id", "run_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("train.id"))
    run_date: Mapped[date]
    status: Mapped[RunStatus] = mapped_column(db_enum(RunStatus), default=RunStatus.SCHEDULED)
    chart_prepared_at: Mapped[datetime | None]

    train: Mapped[Train] = relationship()
    classes: Mapped[list["TrainRunClass"]] = relationship(
        back_populates="run", order_by="TrainRunClass.id", cascade="all, delete-orphan"
    )


class TrainRunClass(Base):
    """Inventory of one class on one train run. Locked while booking or cancelling."""

    __tablename__ = "train_run_class"
    __table_args__ = (UniqueConstraint("run_id", "travel_class"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("train_run.id", ondelete="CASCADE"))
    travel_class: Mapped[TravelClass] = mapped_column(db_enum(TravelClass))
    berth_capacity: Mapped[int]
    waitlist_limit: Mapped[int] = mapped_column(SmallInteger, default=20)
    # Coach composition at the time the run was generated: [{"code": "S1", "berths": 72}].
    coaches: Mapped[list[dict[str, Any]]]

    run: Mapped[TrainRun] = relationship(back_populates="classes")
