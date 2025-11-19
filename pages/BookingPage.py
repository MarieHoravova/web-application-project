from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.BookingService import BookingService
from dependencies import booking_service

router = APIRouter()


@router.get("/", name="bookings_list")
async def bookings_list(
    request: Request,
    user_id: Optional[int] = None,
    svc: BookingService = Depends(booking_service),
):
    if user_id is not None:
        bookings = svc.list_bookings_by_user(user_id)
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
    """
    Jednoduchý formulář – vytvoří booking pro zadané user_id.
    (status = PENDING, kód generuje servis)
    """
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
):
    booking = svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "bookings/booking_detail.html",
        {
            "request": request,
            "title": f"Booking {booking['code']}",
            "booking": booking,
        },
    )
