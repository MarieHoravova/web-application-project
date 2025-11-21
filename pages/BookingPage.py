from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.BookingService import BookingService
from services.BookingStatusService import BookingStatusService
from dependencies import booking_service, booking_status_service
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER
from auth_dependencies import get_current_user

router = APIRouter()

def _profile_role_flags(current_user: dict) -> dict:
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
        "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
    }


@router.get("/", name="bookings_list")
async def bookings_list(
    request: Request,
    user_id: Optional[int] = None,
    svc: BookingService = Depends(booking_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    role_id = current_user["role_id"]
    current_user_id = current_user["id"]

    if flags["is_customer"]:
        bookings: List[Dict[str, Any]] = svc.list_bookings_by_user(current_user_id)
        filter_user_id = current_user_id
    else:
        if user_id is not None:
            bookings = svc.list_bookings_by_user(user_id)
            filter_user_id = user_id
        else:
            bookings = svc.list_bookings()
            filter_user_id = None

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "bookings/bookings_list.html",
        {
            "request": request,
            "title": "Seznam bookingů",
            "bookings": bookings,
            "filter_user_id": filter_user_id,
            "current_user": current_user,
            **flags,  # ← tady pošleme is_admin, is_receptionist, is_customer, is_admin_or_receptionist
        },
    )


@router.post("/", name="bookings_create")
async def bookings_create(
    request: Request,
    user_id: int = Form(...),
    svc: BookingService = Depends(booking_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    # vytvoření bookingu jen ADMIN/RECEPCE (klidně si to časem změň)
    if current_user["role_id"] not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění vytvářet bookingy")

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
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    booking = svc.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nenalezen")

    # pokud bys chtěla, můžeš tady ještě vynutit,
    # že zákazník uvidí jen své vlastní bookingy
    # if current_user["role_id"] == ROLE_CUSTOMER and booking["user_id"] != current_user["id"]:
    #     raise HTTPException(status_code=403, detail="Nemáte přístup k tomuto bookingu")

    statuses = status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "bookings/booking_detail.html",
        {
            "request": request,
            "title": f"Booking {booking['code']}",
            "booking": booking,
            "statuses": statuses,
            "current_user": current_user,
            "is_admin_or_receptionist": current_user["role_id"] in (ROLE_ADMIN, ROLE_RECEPTIONIST),
            "is_customer": current_user["role_id"] == ROLE_CUSTOMER,
        },
    )


@router.post("/{booking_id}/status", name="booking_update_status")
async def booking_update_status(
    booking_id: int,
    request: Request,
    new_status_id: int = Form(...),
    svc: BookingService = Depends(booking_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    current_user_id = current_user["id"]
    current_user_role = current_user["role_id"]

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
