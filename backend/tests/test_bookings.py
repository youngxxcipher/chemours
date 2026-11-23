def test_list_bookings_for_date(client):
    res = client.get("/bookings", params={"date": "2026-12-07"})
    assert res.status_code == 200
    bookings = res.json()
    assert len(bookings) == 8
    starts = [b["start"] for b in bookings]
    assert starts == sorted(starts)


def test_list_bookings_for_room(client):
    res = client.get("/bookings", params={"date": "2026-12-07", "room_id": 3})
    assert [b["title"] for b in res.json()] == ["Standup sync", "Retro"]


def test_create_booking(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 2,
            "title": "Pairing",
            "attendee_ids": [2, 6],
            "start": "2026-12-07T15:00:00",
            "end": "2026-12-07T15:30:00",
        },
    )
    assert res.status_code == 201
    body = res.json()
    assert body["room"]["name"] == "Huddle"
    assert {a["name"] for a in body["attendees"]} == {"Ben", "Farah"}


def test_overlapping_booking_is_rejected(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-07T10:30:00",
            "end": "2026-12-07T11:00:00",
        },
    )
    assert res.status_code == 409


def test_back_to_back_booking_is_allowed(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "attendee_ids": [1],
            "start": "2026-12-07T11:30:00",
            "end": "2026-12-07T12:00:00",
        },
    )
    assert res.status_code == 201


def test_end_must_be_after_start(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 1,
            "creator_id": 1,
            "start": "2026-12-07T11:00:00",
            "end": "2026-12-07T10:00:00",
        },
    )
    assert res.status_code == 422


def test_unknown_room(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 99,
            "creator_id": 1,
            "start": "2026-12-07T10:00:00",
            "end": "2026-12-07T11:00:00",
        },
    )
    assert res.status_code == 404


def test_unknown_attendee(client):
    res = client.post(
        "/bookings",
        json={
            "room_id": 3,
            "creator_id": 1,
            "attendee_ids": [42],
            "start": "2026-12-07T15:00:00",
            "end": "2026-12-07T15:30:00",
        },
    )
    assert res.status_code == 400
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Booking
from app.routers.bookings import create_booking
from app.schemas import BookingIn
from app.seed import seed




def test_concurrent_overlapping_booking_allows_exactly_one():
    database_name = uuid4().hex
    engine = create_engine(
        f"sqlite:///file:{database_name}?mode=memory&cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestSession() as db:
        seed(db)

    payload = BookingIn(
        room_id=3,
        creator_id=2,
        attendee_ids=[2],
        start="2026-12-10T10:00:00",
        end="2026-12-10T10:30:00",
    )

    def attempt_booking():
        with TestSession() as db:
            try:
                create_booking(payload, db)
                return 201
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _: attempt_booking(), range(2)))

    with TestSession() as db:
        created = db.query(Booking).filter_by(room_id=3).all()
    engine.dispose()

    assert sorted(statuses) == [201, 409]
    assert len([booking for booking in created if booking.start == payload.start]) == 1
