from datetime import date, timedelta
from typing import List, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse

from services.ReservationService import ReservationService
from services.ReservationItemService import ReservationItemService
from services.ContactMessageService import ContactMessageService

from dependencies import reservation_service, reservation_item_service, contact_message_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

router = APIRouter()


def _profile_role_flags(current_user: dict) -> dict:
    """Společná helper funkce – stejná jako v UserPage."""
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
    }


@router.get("/profile", name="user_profile")
async def user_profile(
    request: Request,
    reservation_svc: ReservationService = Depends(reservation_service),
    reservation_item_svc: ReservationItemService = Depends(reservation_item_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    role_id = current_user["role_id"]
    user_id = current_user["id"]

    # ---- data pro hosta (customer) – hlavičky rezervací ----
    customer_reservations: List[Dict[str, Any]] = []
    last_reservation: Dict[str, Any] | None = None
    if flags["is_customer"]:
        customer_reservations = reservation_svc.list_reservations_by_user(user_id)
        last_reservation = customer_reservations[0] if customer_reservations else None

    # ---- data pro recepci a admina – nadcházející pobyty (items) ----
    upcoming_reservations: List[Dict[str, Any]] = []
    if flags["is_receptionist"] or flags["is_admin"]:
        today = date.today()
        date_from = today.isoformat()
        date_to = (today + timedelta(days=7)).isoformat()
        upcoming_reservations = reservation_item_svc.list_reservation_items_in_period(
            date_from, date_to
        )

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_overview.html",
        {
            "request": request,
            "title": "Můj profil",
            "current_user": current_user,
            "customer_reservations": customer_reservations,
            "last_reservation": last_reservation,
            "upcoming_reservations": upcoming_reservations,
            **flags,
        },
    )


@router.get("/profile/messages", name="contact_messages_list")
async def contact_messages_list(
    request: Request,
    contact_svc: ContactMessageService = Depends(contact_message_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)

    # Jen admin + recepce
    if not (flags["is_admin"] or flags["is_receptionist"]):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit zprávy z kontaktu")

    messages = contact_svc.list_contact_messages(current_user_role=current_user["role_id"])

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_contact_messages.html",
        {
            "request": request,
            "title": "Přijaté zprávy",
            "current_user": current_user,
            "contact_messages": messages,
            **flags,
        },
    )


@router.get("/profile/terms", name="profile_terms")
async def profile_terms(
    request: Request,
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_terms.html",
        {
            "request": request,
            "title": "Podmínky a souhlasy",
            "current_user": current_user,
            **flags,
        },
    )
