from datetime import date, time

from sqlalchemy import ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import TravelClass, db_enum


class Station(Base):
    __tablename__ = "station"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    city: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(default=True)


class Train(Base):
    __tablename__ = "train"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(5), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    # Bit 0 = Monday ... bit 6 = Sunday.
    running_days: Mapped[int] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(default=True)

    stops: Mapped[list["RouteStop"]] = relationship(
        order_by="RouteStop.seq", cascade="all, delete-orphan"
    )
    coaches: Mapped[list["Coach"]] = relationship(
        order_by="Coach.code", cascade="all, delete-orphan"
    )

    def runs_on(self, day: date) -> bool:
        return bool(self.running_days & (1 << day.weekday()))


class RouteStop(Base):
    __tablename__ = "route_stop"
    __table_args__ = (
        UniqueConstraint("train_id", "seq"),
        UniqueConstraint("train_id", "station_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("train.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(SmallInteger)
    station_id: Mapped[int] = mapped_column(ForeignKey("station.id"))
    arrival: Mapped[time | None]
    departure: Mapped[time | None]
    day_offset: Mapped[int] = mapped_column(SmallInteger, default=0)
    distance_km: Mapped[int]

    station: Mapped[Station] = relationship(lazy="joined")


class Coach(Base):
    __tablename__ = "coach"
    __table_args__ = (UniqueConstraint("train_id", "code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    train_id: Mapped[int] = mapped_column(ForeignKey("train.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(4))
    travel_class: Mapped[TravelClass] = mapped_column(db_enum(TravelClass))
    berth_count: Mapped[int] = mapped_column(SmallInteger)
