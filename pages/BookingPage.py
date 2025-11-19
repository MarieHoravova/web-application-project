from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.BookingService import BookingService
from services.BookingStatusService import BookingStatusService
from dependencies import booking_service, booking_status_service
from domain.constants import ROLE_ADMIN  # zatím napevno, než napojíš přihlášení

router = APIRouter()


@router.get("/", name="bookings_list")
async def bookings_list(
    request: Request,
    user_id: Optional[int] = None,
    svc: BookingService = Depends(booking_service),
):
    if user_id is not None:
        bookings: List[Dict[str, Any]] = svc.list_bookings_by_user(user_id)
    else:
        bookings = svc.list_bookings()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "bookings/bookings_list.html",
        {
            "request": request,
            "title": "Seznam bookingů",
            "bookings": bookings,
            "filter_user_id": user_id,
        },
    )


@router.post("/", name="bookings_create")
async def bookings_create(
    request: Request,
    user_id: int = Form(...),
    svc: BookingService = Depends(booking_service),
):
    svc.create_booking(user_id=user_id)

    return RedirectResponse(
        url=request.url_for("bookings_list"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{booking_id}", name="booking_detail")
async def booking_detail(
    booking_id: int,
    request: Request,
    svc: BookingService = Depends(booking_service),
    status_svc: BookingStatusService = Depends(booking_status_service),
):
    booking = svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    statuses = status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "bookings/booking_detail.html",
        {
            "request": request,
            "title": f"Booking {booking['code']}",
            "booking": booking,
            "statuses": statuses,
        },
    )


@router.post("/{booking_id}/status", name="booking_update_status")
async def booking_update_status(
    booking_id: int,
    request: Request,
    new_status_id: int = Form(...),
    svc: BookingService = Depends(booking_service),
):
    # TODO: až napojíš autentizaci, vezmeš current_user_id a role z JWT
    current_user_id = 1
    current_user_role = ROLE_ADMIN  # recepční by byla ROLE_RECEPTIONIST

    try:
        svc.update_booking_status(
            booking_id=booking_id,
            new_status_id=new_status_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("booking_detail", booking_id=booking_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
