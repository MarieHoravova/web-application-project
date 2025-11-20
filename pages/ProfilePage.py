# pages/ProfilePage.py
from datetime import date, timedelta
from typing import List, Dict, Any

from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

from services.BookingService import BookingService
from services.ReservationService import ReservationService
from dependencies import booking_service, reservation_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

router = APIRouter()

@router.get("/profile", name="user_profile")
async def user_profile(
    request: Request,
    booking_svc: BookingService = Depends(booking_service),
    res_svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]
    user_id = current_user["id"]

    is_admin = role_id == ROLE_ADMIN
    is_receptionist = role_id == ROLE_RECEPTIONIST
    is_customer = role_id == ROLE_CUSTOMER

    # --- zákazník: jeho bookingy + poslední booking ---
    customer_bookings: List[Dict[str, Any]] = []
    last_booking: Dict[str, Any] | None = None
    if is_customer:
        customer_bookings = booking_svc.list_bookings_by_user(user_id)
        last_booking = customer_bookings[0] if customer_bookings else None

    # --- recepce / admin: nejbližší rezervace ---
    upcoming_reservations: List[Dict[str, Any]] = []
    if is_receptionist or is_admin:
        today = date.today()
        date_from = today.isoformat()
        date_to = (today + timedelta(days=7)).isoformat()
        upcoming_reservations = res_svc.list_reservations_in_period(date_from, date_to)

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_overview.html",
        {
            "request": request,
            "title": "Můj profil",
            "current_user": current_user,
            "is_admin": is_admin,
            "is_receptionist": is_receptionist,
            "is_customer": is_customer,
            "customer_bookings": customer_bookings,
            "last_booking": last_booking,
            "upcoming_reservations": upcoming_reservations,
        },
    )
