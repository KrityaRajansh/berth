from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

from app.core.clock import IST

# Every time in API responses is given in Indian Standard Time, e.g. 2026-11-02T06:00:00+05:30.
IstDatetime = Annotated[
    datetime,
    PlainSerializer(lambda value: value.astimezone(IST).isoformat(), return_type=str),
]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class StationRef(Schema):
    code: str
    name: str
