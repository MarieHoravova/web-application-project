from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.ReservationService import ReservationService
from services.BookingService import BookingService
from dependencies import reservation_service, booking_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST

router = APIRouter()


@router.get("/booking/{booking_id}", name="reservations_by_booking")
async def reservations_by_booking(
    booking_id: int,
    request: Request,
    res_svc: ReservationService = Depends(reservation_service),
    booking_svc: BookingService = Depends(booking_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    booking = booking_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    try:
        reservations: List[Dict[str, Any]] = res_svc.list_reservations_by_booking(
            booking_id=booking_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservations_by_booking.html",
        {
            "request": request,
            "title": f"Rezervace pro booking {booking['code']}",
            "booking": booking,
            "reservations": reservations,
            "current_user": current_user,
            "is_admin_or_receptionist": current_user["role_id"] in (ROLE_ADMIN, ROLE_RECEPTIONIST),
        },
    )


@router.post("/booking/{booking_id}", name="reservations_create_for_booking")
async def reservations_create_for_booking(
    booking_id: int,
    request: Request,
    room_id: int = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    adults: int = Form(...),
    children: int = Form(0),
    res_svc: ReservationService = Depends(reservation_service),
    booking_svc: BookingService = Depends(booking_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    booking = booking_svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    try:
        res_svc.create_reservation(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            booking_id=booking_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("reservations_by_booking", booking_id=booking_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/booking/{booking_id}/delete/{reservation_id}", name="reservation_delete")
async def reservation_delete(
    booking_id: int,
    reservation_id: int,
    request: Request,
    res_svc: ReservationService = Depends(reservation_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    try:
        res_svc.delete_reservation(
            reservation_id=reservation_id,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("reservations_by_booking", booking_id=booking_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
