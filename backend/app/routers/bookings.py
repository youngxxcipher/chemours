from datetime import date, datetime, time, timedelta
from time import monotonic, sleep

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Booking, Room, User
from ..scheduling import overlaps
from ..schemas import BookingIn, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.get("", response_model=list[BookingOut])
def list_bookings(
    date: date | None = None,
    room_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = (
        select(Booking)
        .options(selectinload(Booking.attendees), selectinload(Booking.room))
        .order_by(Booking.start)
    )
    if date is not None:
        day_start = datetime.combine(date, time.min)
        query = query.where(Booking.start >= day_start, Booking.start < day_start + timedelta(days=1))
    if room_id is not None:
        query = query.where(Booking.room_id == room_id)
    return db.scalars(query).all()


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingIn, db: Session = Depends(get_db)):
    # PostgreSQL serializes attempts for the same room with a row lock. SQLite
    # does not implement row locks, so take its write lock before checking
    # availability. In both cases, the check and insert share one transaction.
    if db.bind.dialect.name == "sqlite":
        lock_deadline = monotonic() + 2
        while True:
            try:
                db.execute(text("BEGIN IMMEDIATE"))
                break
            except OperationalError as error:
                db.rollback()
                if "locked" not in str(error).lower():
                    raise
                if monotonic() >= lock_deadline:
                    raise HTTPException(
                        status_code=409,
                        detail="Room is currently being booked; please retry",
                    )
                sleep(0.01)

    room = db.scalar(select(Room).where(Room.id == payload.room_id).with_for_update())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    if db.get(User, payload.creator_id) is None:
        raise HTTPException(status_code=404, detail="Creator not found")

    attendee_ids = set(payload.attendee_ids)
    attendees = db.scalars(select(User).where(User.id.in_(attendee_ids))).all()
    if len(attendees) != len(attendee_ids):
        raise HTTPException(status_code=400, detail="Unknown attendee")

    existing = db.scalars(select(Booking).where(Booking.room_id == room.id)).all()
    for other in existing:
        if overlaps(other.start, other.end, payload.start, payload.end):
            raise HTTPException(status_code=409, detail="Room is already booked for that time")

    booking = Booking(
        room_id=room.id,
        creator_id=payload.creator_id,
        title=payload.title,
        start=payload.start,
        end=payload.end,
        attendees=list(attendees),
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
