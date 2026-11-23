from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Role = Literal["employee", "manager", "intern"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    role: Role


class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    capacity: int = Field(gt=0, le=100)


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class BookingIn(BaseModel):
    room_id: int
    creator_id: int
    title: str = Field(default="", max_length=200)
    attendee_ids: list[int] = Field(default_factory=list)
    start: datetime
    end: datetime

    @field_validator("start", "end")
    @classmethod
    def normalise_datetime(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=None, second=0, microsecond=0)

    @model_validator(mode="after")
    def check_order(self) -> "BookingIn":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    room: RoomOut
    creator_id: int
    attendees: list[UserOut]
    start: datetime
    end: datetime


class SlotSuggestionIn(BaseModel):
    requester_id: int
    attendee_ids: list[int] = Field(default_factory=list)
    duration_minutes: int
    date: date

    @field_validator("duration_minutes")
    @classmethod
    def validate_duration(cls, value: int) -> int:
        if not 15 <= value <= 240 or value % 15:
            raise ValueError("duration_minutes must be a multiple of 15 from 15 to 240")
        return value


class SlotOut(BaseModel):
    start: datetime
    end: datetime


class SlotSuggestionOut(BaseModel):
    slots: list[SlotOut]
