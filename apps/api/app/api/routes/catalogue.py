"""Public endpoints: stations, train search, train routes and PNR status."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ClockDep, SessionDep
from app.models.enums import TravelClass
from app.repositories.network import StationRepository
from app.schemas.booking import PnrStatusOut
from app.schemas.network import StationOut, TrainOut
from app.schemas.search import SearchResult
from app.services.network import NetworkService, train_out
from app.services.search import SearchService
from app.services.tickets import TicketService

router = APIRouter(tags=["catalogue"])


@router.get("/stations")
def suggest_stations(
    session: SessionDep, q: Annotated[str, Query(min_length=1, max_length=40)]
) -> list[StationOut]:
    return [StationOut.model_validate(s) for s in StationRepository(session).suggest(q)]


@router.get("/trains/search")
def search_trains(
    session: SessionDep,
    clock: ClockDep,
    from_: Annotated[str, Query(alias="from", min_length=2, max_length=8)],
    to: Annotated[str, Query(min_length=2, max_length=8)],
    date_: Annotated[date, Query(alias="date")],
    cls: TravelClass | None = None,
) -> list[SearchResult]:
    return SearchService(session, clock).search(from_, to, date_, cls)


@router.get("/trains/{number}/route")
def train_route(number: str, session: SessionDep) -> TrainOut:
    return train_out(NetworkService(session).get_train(number))


@router.get("/pnr/{pnr}")
def pnr_status(pnr: str, session: SessionDep, clock: ClockDep) -> PnrStatusOut:
    return TicketService(session, clock).pnr_status(pnr)
