from datetime import time
from typing import Annotated

from pydantic import Field, model_validator

from app.models.enums import TravelClass
from app.schemas.common import Schema

StationCode = Annotated[str, Field(pattern=r"^[A-Z]{2,8}$")]


class StationOut(Schema):
    id: int
    code: str
    name: str
    city: str
    is_active: bool


class StationIn(Schema):
    code: StationCode
    name: str = Field(min_length=2, max_length=80)
    city: str = Field(min_length=2, max_length=80)
    is_active: bool = True


class RouteStopIn(Schema):
    station_code: StationCode
    arrival: time | None = None
    departure: time | None = None
    day_offset: int = Field(ge=0, le=6)
    distance_km: int = Field(ge=0, le=5000)

    @model_validator(mode="after")
    def has_a_time(self) -> "RouteStopIn":
        if self.arrival is None and self.departure is None:
            raise ValueError("A stop needs an arrival or a departure time.")
        return self


class RouteStopOut(Schema):
    seq: int
    station_code: str
    station_name: str
    arrival: time | None
    departure: time | None
    day_offset: int
    distance_km: int


class CoachIn(Schema):
    code: str = Field(pattern=r"^[A-Z]{1,2}\d{1,2}$")
    travel_class: TravelClass
    berth_count: int = Field(ge=1, le=72)


class CoachOut(CoachIn):
    pass


class TrainIn(Schema):
    number: str = Field(pattern=r"^\d{5}$")
    name: str = Field(min_length=3, max_length=80)
    running_days: list[int] = Field(min_length=1, max_length=7, description="0 = Monday")
    is_active: bool = True

    @model_validator(mode="after")
    def valid_days(self) -> "TrainIn":
        if any(d < 0 or d > 6 for d in self.running_days):
            raise ValueError("Running days must be between 0 (Monday) and 6 (Sunday).")
        return self


class TrainOut(Schema):
    id: int
    number: str
    name: str
    running_days: list[int]
    is_active: bool
    stops: list[RouteStopOut]
    coaches: list[CoachOut]
