"""Load demo data: real station codes, invented trains, and optional accounts.

Safe to run more than once; existing stations, trains and users are left alone.

    uv run python -m scripts.seed

Accounts are created only when their passwords are set in the environment:
SEED_ADMIN_PASSWORD (admin@example.com) and SEED_DEMO_PASSWORD (demo@example.com).
"""

import os
from datetime import time, timedelta

from sqlalchemy import select

from app.core.clock import SystemClock, today_ist
from app.core.db import get_sessionmaker
from app.core.security import hash_password
from app.models import Coach, RouteStop, Station, Train, User
from app.models.enums import Role, TravelClass
from app.services.runs import RunService
from app.services.schedule import ADVANCE_RESERVATION_DAYS

STATIONS = [
    ("NDLS", "New Delhi", "Delhi"),
    ("MTJ", "Mathura Jn", "Mathura"),
    ("AGC", "Agra Cantt", "Agra"),
    ("GWL", "Gwalior Jn", "Gwalior"),
    ("VGLJ", "Virangana Lakshmibai Jhansi", "Jhansi"),
    ("BPL", "Bhopal Jn", "Bhopal"),
    ("ET", "Itarsi Jn", "Itarsi"),
    ("NGP", "Nagpur Jn", "Nagpur"),
    ("KOTA", "Kota Jn", "Kota"),
    ("RTM", "Ratlam Jn", "Ratlam"),
    ("BRC", "Vadodara Jn", "Vadodara"),
    ("ST", "Surat", "Surat"),
    ("MMCT", "Mumbai Central", "Mumbai"),
    ("CNB", "Kanpur Central", "Kanpur"),
    ("PRYJ", "Prayagraj Jn", "Prayagraj"),
    ("DDU", "Pt. Deen Dayal Upadhyaya Jn", "Mughalsarai"),
    ("PNBE", "Patna Jn", "Patna"),
    ("HWH", "Howrah Jn", "Kolkata"),
    ("MAS", "MGR Chennai Central", "Chennai"),
    ("BZA", "Vijayawada Jn", "Vijayawada"),
    ("SC", "Secunderabad Jn", "Hyderabad"),
    ("SBC", "KSR Bengaluru", "Bengaluru"),
]

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
DAILY = list(range(7))

LONG_DISTANCE = [
    ("S1", "SL", 72),
    ("S2", "SL", 72),
    ("S3", "SL", 72),
    ("S4", "SL", 72),
    ("B1", "3A", 64),
    ("B2", "3A", 64),
    ("B3", "3A", 64),
    ("A1", "2A", 48),
    ("A2", "2A", 48),
    ("H1", "1A", 24),
]
DAY_TRAIN = [("S1", "SL", 72), ("S2", "SL", 72), ("B1", "3A", 64), ("A1", "2A", 48)]


def t(value: str | None) -> time | None:
    return time.fromisoformat(value) if value else None


# (code, arrival, departure, day offset of arrival, km)
TRAINS = [
    (
        "22401",
        "Capital Western Express",
        DAILY,
        LONG_DISTANCE,
        [
            ("NDLS", None, "16:30", 0, 0),
            ("MTJ", "18:05", "18:07", 0, 141),
            ("KOTA", "22:10", "22:20", 0, 465),
            ("RTM", "01:50", "01:55", 1, 730),
            ("BRC", "05:05", "05:15", 1, 991),
            ("ST", "06:55", "07:00", 1, 1120),
            ("MMCT", "09:35", None, 1, 1384),
        ],
    ),
    (
        "22402",
        "Capital Western Express",
        DAILY,
        LONG_DISTANCE,
        [
            ("MMCT", None, "17:00", 0, 0),
            ("ST", "19:40", "19:45", 0, 264),
            ("BRC", "21:15", "21:25", 0, 393),
            ("RTM", "00:40", "00:45", 1, 654),
            ("KOTA", "04:20", "04:30", 1, 919),
            ("MTJ", "08:20", "08:22", 1, 1243),
            ("NDLS", "10:00", None, 1, 1384),
        ],
    ),
    (
        "12611",
        "Central Plains Express",
        [MON, WED, FRI],
        LONG_DISTANCE,
        [
            ("NDLS", None, "06:00", 0, 0),
            ("AGC", "08:30", "08:35", 0, 195),
            ("GWL", "09:55", "10:00", 0, 313),
            ("VGLJ", "11:20", "11:28", 0, 411),
            ("BPL", "15:30", "15:40", 0, 702),
            ("ET", "17:10", "17:15", 0, 794),
            ("NGP", "22:30", None, 0, 1090),
        ],
    ),
    (
        "12612",
        "Central Plains Express",
        [TUE, THU, SAT],
        LONG_DISTANCE,
        [
            ("NGP", None, "07:00", 0, 0),
            ("ET", "12:15", "12:20", 0, 296),
            ("BPL", "13:50", "14:00", 0, 388),
            ("VGLJ", "18:00", "18:08", 0, 679),
            ("GWL", "19:30", "19:35", 0, 777),
            ("AGC", "20:55", "21:00", 0, 895),
            ("NDLS", "23:30", None, 0, 1090),
        ],
    ),
    (
        "12345",
        "Eastern Ganga Mail",
        DAILY,
        LONG_DISTANCE,
        [
            ("NDLS", None, "20:10", 0, 0),
            ("CNB", "01:50", "01:58", 1, 440),
            ("PRYJ", "04:20", "04:30", 1, 634),
            ("DDU", "07:15", "07:25", 1, 787),
            ("PNBE", "10:30", "10:40", 1, 999),
            ("HWH", "19:45", None, 1, 1531),
        ],
    ),
    (
        "12346",
        "Eastern Ganga Mail",
        DAILY,
        LONG_DISTANCE,
        [
            ("HWH", None, "08:15", 0, 0),
            ("PNBE", "17:10", "17:20", 0, 532),
            ("DDU", "20:30", "20:40", 0, 744),
            ("PRYJ", "23:20", "23:30", 0, 897),
            ("CNB", "02:00", "02:08", 1, 1091),
            ("NDLS", "07:40", None, 1, 1531),
        ],
    ),
    (
        "16521",
        "Deccan Coast Express",
        [TUE, THU, SAT],
        LONG_DISTANCE,
        [
            ("MAS", None, "21:00", 0, 0),
            ("BZA", "03:30", "03:45", 1, 431),
            ("SC", "09:30", None, 1, 781),
        ],
    ),
    (
        "16522",
        "Deccan Coast Express",
        [MON, WED, FRI],
        LONG_DISTANCE,
        [
            ("SC", None, "18:00", 0, 0),
            ("BZA", "23:30", "23:45", 0, 350),
            ("MAS", "06:10", None, 1, 781),
        ],
    ),
    (
        "16525",
        "Garden City Express",
        DAILY,
        DAY_TRAIN,
        [
            ("MAS", None, "07:00", 0, 0),
            ("SBC", "12:30", None, 0, 362),
        ],
    ),
    (
        "16526",
        "Garden City Express",
        DAILY,
        DAY_TRAIN,
        [
            ("SBC", None, "14:30", 0, 0),
            ("MAS", "20:00", None, 0, 362),
        ],
    ),
]


def seed() -> None:
    with get_sessionmaker()() as session:
        existing = set(session.scalars(select(Station.code)))
        session.add_all(
            Station(code=c, name=n, city=city) for c, n, city in STATIONS if c not in existing
        )
        session.flush()
        station_id = {code: id_ for code, id_ in session.execute(select(Station.code, Station.id))}

        trains_added = 0
        known = set(session.scalars(select(Train.number)))
        for number, name, days, coaches, stops in TRAINS:
            if number in known:
                continue
            train = Train(number=number, name=name, running_days=sum(1 << d for d in days))
            train.stops = [
                RouteStop(
                    seq=i,
                    station_id=station_id[code],
                    arrival=t(arr),
                    departure=t(dep),
                    day_offset=offset,
                    distance_km=km,
                )
                for i, (code, arr, dep, offset, km) in enumerate(stops, start=1)
            ]
            train.coaches = [
                Coach(code=code, travel_class=TravelClass(cls), berth_count=n)
                for code, cls, n in coaches
            ]
            session.add(train)
            trains_added += 1

        users_added = 0
        for email, name, mobile, role, env in [
            ("admin@example.com", "Berth Admin", "9000000100", Role.ADMIN, "SEED_ADMIN_PASSWORD"),
            (
                "demo@example.com",
                "Demo Passenger",
                "9000000101",
                Role.PASSENGER,
                "SEED_DEMO_PASSWORD",
            ),
        ]:
            password = os.environ.get(env)
            if not password or session.scalar(select(User).where(User.email == email)):
                continue
            session.add(
                User(
                    full_name=name,
                    email=email,
                    mobile=mobile,
                    password_hash=hash_password(password),
                    role=role,
                )
            )
            users_added += 1
        session.commit()

        today = today_ist(SystemClock())
        runs = RunService(session).generate(today, today + timedelta(days=ADVANCE_RESERVATION_DAYS))

    print(f"stations: {len(STATIONS) - len(existing & {s[0] for s in STATIONS})} added")
    print(f"trains: {trains_added} added, runs: {runs} added, users: {users_added} added")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    seed()
