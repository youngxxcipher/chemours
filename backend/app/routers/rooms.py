from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..db import get_db
from ..models import Booking, Room, User
from ..scheduling import (
    WORKDAY_END,
    WORKDAY_START,
    overlaps,
    overlaps_lunch,
    room_intervals_conflict,
)
from ..schemas import RoomIn, RoomOut, SlotOut, SlotSuggestionIn, SlotSuggestionOut

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).order_by(Room.id)).all()


@router.get("/{room_id}", response_model=RoomOut)
def get_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


@router.post("", response_model=RoomOut, status_code=201)
def create_room(payload: RoomIn, db: Session = Depends(get_db)):
    room = Room(name=payload.name, capacity=payload.capacity)
    db.add(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A room with that name already exists")
    return room


@router.post("/{room_id}/suggest", response_model=SlotSuggestionOut)
def suggest_slots(room_id: int, payload: SlotSuggestionIn, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")

    requester = db.get(User, payload.requester_id)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requester not found")
    if room.name == "Board Room" and requester.role == "intern":
        raise HTTPException(status_code=403, detail="Interns cannot book the Board Room")

    attendee_ids = set(payload.attendee_ids)
    attendees = db.scalars(select(User).where(User.id.in_(attendee_ids))).all()
    if len(attendees) != len(attendee_ids):
        raise HTTPException(status_code=400, detail="Unknown attendee")
    participant_ids = attendee_ids | {requester.id}

    if payload.date.weekday() >= 5:
        return SlotSuggestionOut(slots=[])

    bookings = db.scalars(select(Booking).options(selectinload(Booking.attendees))).all()
    room_bookings = [booking for booking in bookings if booking.room_id == room.id]
    participant_bookings = [
        booking
        for booking in bookings
        if participant_ids & {attendee.id for attendee in booking.attendees}
    ]

    duration = timedelta(minutes=payload.duration_minutes)
    day_start = datetime.combine(payload.date, WORKDAY_START)
    day_end = datetime.combine(payload.date, WORKDAY_END)
    slots: list[SlotOut] = []
    candidate_start = day_start
    ist = ZoneInfo("Asia/Kolkata")

    while candidate_start + duration <= day_end and len(slots) < 3:
        candidate_end = candidate_start + duration
        room_is_busy = any(
            room_intervals_conflict(
                booking.start, booking.end, candidate_start, candidate_end
            )
            for booking in room_bookings
        )
        participant_is_busy = any(
            overlaps(booking.start, booking.end, candidate_start, candidate_end)
            for booking in participant_bookings
        )
        lunch_is_blocked = payload.duration_minutes > 30 and overlaps_lunch(
            candidate_start, candidate_end
        )
        if not room_is_busy and not participant_is_busy and not lunch_is_blocked:
            slots.append(
                SlotOut(
                    start=candidate_start.replace(tzinfo=ist),
                    end=candidate_end.replace(tzinfo=ist),
                )
            )
        candidate_start += timedelta(minutes=15)

    return SlotSuggestionOut(slots=slots)
