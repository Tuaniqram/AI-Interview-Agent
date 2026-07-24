from __future__ import annotations

from datetime import date, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class SlotCreate(BaseModel):
    title: Optional[str] = None
    duration_min: int = 45
    buffer_min: int = 5


class SlotResponse(BaseModel):
    id: UUID
    org_id: UUID
    title: Optional[str] = None
    duration_min: int
    buffer_min: int
    is_active: bool

    model_config = {"from_attributes": True}


class AvailabilityBatchCreate(BaseModel):
    slot_id: UUID
    date: date
    start_time: time
    end_time: time


class AvailabilityResponse(BaseModel):
    id: UUID
    slot_id: UUID
    date: date
    start_time: time
    end_time: time
    is_booked: bool

    model_config = {"from_attributes": True}


class AvailableSlotResponse(BaseModel):
    availability_id: UUID
    slot_id: UUID
    title: Optional[str] = None
    date: date
    start_time: time
    end_time: time
    duration_min: int


class BookSlotRequest(BaseModel):
    availability_id: UUID
    candidate_email: str
    candidate_name: str


class BookingResponse(BaseModel):
    id: UUID
    slot_id: UUID
    availability_id: UUID
    candidate_email: str
    candidate_name: str
    status: str
    booked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


from datetime import datetime
