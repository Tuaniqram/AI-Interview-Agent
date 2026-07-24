from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.rbac import require_org_role, resolve_org_id
from app.database.deps import get_db
from app.scheduling.schemas import (
    AvailabilityBatchCreate,
    AvailabilityResponse,
    AvailableSlotResponse,
    BookingResponse,
    BookSlotRequest,
    SlotCreate,
    SlotResponse,
)
from app.scheduling.service import (
    book_slot,
    cancel_booking,
    create_slot,
    get_available_slots,
    list_slots,
    set_availability,
)

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


@router.post("/slots", response_model=SlotResponse)
async def create_slot_endpoint(
    req: SlotCreate,
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner"])),
    db: AsyncSession = Depends(get_db),
):
    return await create_slot(org_id, req, db)


@router.get("/slots", response_model=list[SlotResponse])
async def list_slots_endpoint(
    org_id: str = Depends(resolve_org_id),
    _: None = Depends(require_org_role(["owner", "member", "viewer"])),
    db: AsyncSession = Depends(get_db),
):
    return await list_slots(org_id, db)


@router.post("/availability", response_model=AvailabilityResponse)
async def set_availability_endpoint(
    req: AvailabilityBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    return await set_availability(req, db)


@router.get("/available", response_model=list[AvailableSlotResponse])
async def get_available_endpoint(
    org_id: str = Depends(resolve_org_id),
    db: AsyncSession = Depends(get_db),
):
    return await get_available_slots(org_id, db)


@router.post("/book", response_model=BookingResponse)
async def book_slot_endpoint(
    req: BookSlotRequest,
    db: AsyncSession = Depends(get_db),
):
    return await book_slot(req, db)


@router.post("/bookings/{booking_id}/cancel", status_code=204)
async def cancel_booking_endpoint(
    booking_id: str,
    db: AsyncSession = Depends(get_db),
):
    await cancel_booking(booking_id, db)
