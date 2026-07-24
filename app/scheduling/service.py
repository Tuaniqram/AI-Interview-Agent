from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.deps import get_db
from app.models.db import Booking, InterviewSlot, Organization, SlotAvailability, User
from app.scheduling.calendar import generate_slots
from app.scheduling.schemas import (
    AvailabilityBatchCreate,
    AvailabilityResponse,
    AvailableSlotResponse,
    BookingResponse,
    BookSlotRequest,
    SlotCreate,
    SlotResponse,
)


async def create_slot(org_id: str, req: SlotCreate, db: AsyncSession) -> SlotResponse:
    slot = InterviewSlot(
        id=uuid.uuid4(),
        org_id=org_id,
        title=req.title,
        duration_min=req.duration_min,
        buffer_min=req.buffer_min,
    )
    db.add(slot)
    await db.commit()
    await db.refresh(slot)
    return SlotResponse.model_validate(slot)


async def list_slots(org_id: str, db: AsyncSession) -> list[SlotResponse]:
    result = await db.execute(
        select(InterviewSlot).where(
            InterviewSlot.org_id == org_id,
            InterviewSlot.is_active == True,
        )
    )
    return [SlotResponse.model_validate(s) for s in result.scalars().all()]


async def set_availability(req: AvailabilityBatchCreate, db: AsyncSession) -> AvailabilityResponse:
    slot_result = await db.execute(
        select(InterviewSlot).where(InterviewSlot.id == req.slot_id)
    )
    slot = slot_result.scalar_one_or_none()
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")

    avail = SlotAvailability(
        id=uuid.uuid4(),
        slot_id=req.slot_id,
        date=req.date,
        start_time=req.start_time,
        end_time=req.end_time,
    )
    db.add(avail)
    await db.commit()
    await db.refresh(avail)
    return AvailabilityResponse.model_validate(avail)


async def get_available_slots(org_id: str, db: AsyncSession) -> list[AvailableSlotResponse]:
    result = await db.execute(
        select(SlotAvailability, InterviewSlot)
        .join(InterviewSlot, SlotAvailability.slot_id == InterviewSlot.id)
        .where(
            InterviewSlot.org_id == org_id,
            InterviewSlot.is_active == True,
            SlotAvailability.is_booked == False,
            SlotAvailability.date >= date.today(),
        )
        .order_by(SlotAvailability.date, SlotAvailability.start_time)
    )
    slots = []
    for avail, slot in result.all():
        slots.append(AvailableSlotResponse(
            availability_id=avail.id,
            slot_id=slot.id,
            title=slot.title,
            date=avail.date,
            start_time=avail.start_time,
            end_time=avail.end_time,
            duration_min=slot.duration_min,
        ))
    return slots


async def book_slot(req: BookSlotRequest, db: AsyncSession) -> BookingResponse:
    avail_result = await db.execute(
        select(SlotAvailability).where(
            SlotAvailability.id == req.availability_id,
            SlotAvailability.is_booked == False,
        )
    )
    avail = avail_result.scalar_one_or_none()
    if not avail:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot not available")

    avail.is_booked = True
    booking = Booking(
        id=uuid.uuid4(),
        slot_id=avail.slot_id,
        availability_id=avail.id,
        candidate_email=req.candidate_email,
        candidate_name=req.candidate_name,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return BookingResponse.model_validate(booking)


async def cancel_booking(booking_id: str, db: AsyncSession) -> None:
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    booking.status = "cancelled"
    avail_result = await db.execute(
        select(SlotAvailability).where(SlotAvailability.id == booking.availability_id)
    )
    avail = avail_result.scalar_one_or_none()
    if avail:
        avail.is_booked = False
    await db.commit()
