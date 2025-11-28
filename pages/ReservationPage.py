from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from starlette import status

from services.ReservationService import ReservationService
from services.ReservationStatusService import ReservationStatusService
from dependencies import reservation_service, reservation_status_service
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER
from auth_dependencies import get_current_user
from services.ReservationItemService import ReservationItemService
from dependencies import reservation_item_service

router = APIRouter()


def _profile_role_flags(current_user: dict) -> dict:
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
        "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
    }


@router.get("/", name="reservations_list")
async def reservations_list(
    request: Request,
    user_id: Optional[str] = Query(default=None),
    svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    current_user_id = current_user["id"]

    # zákazník vidí jen své rezervace, žádné filtrování
    if flags["is_customer"]:
        reservations: List[Dict[str, Any]] = svc.list_reservations_by_user(current_user_id)
        filter_user_id: Optional[int] = current_user_id

    else:
        # user_id může být:
        # - None (parametr vůbec nepřišel)
        # - "" (vybráno "-- všichni uživatelé --")
        # - "76", "5", ... (konkrétní uživatel)
        if user_id not in (None, ""):
            try:
                user_id_int = int(user_id)
            except ValueError:
                # rozbitý vstup -> ignorujeme filtr, zobrazíme vše
                reservations = svc.list_reservations()
                filter_user_id = None
            else:
                reservations = svc.list_reservations_by_user(user_id_int)
                filter_user_id = user_id_int
        else:
            reservations = svc.list_reservations()
            filter_user_id = None

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_list.html",
        {
            "request": request,
            "title": "Seznam rezervací",
            "reservations": reservations,
            "filter_user_id": filter_user_id,
            "current_user": current_user,
            **flags,
        },
    )


# @router.get("/{reservation_id}", name="reservation_detail")
# async def reservation_detail(
#     reservation_id: int,
#     request: Request,
#     svc: ReservationService = Depends(reservation_service),
#     status_svc: ReservationStatusService = Depends(reservation_status_service),
#     current_user = Depends(get_current_user),
# ):
#     if isinstance(current_user, RedirectResponse):
#         return current_user
#
#     reservation = svc.get_reservation_by_id(reservation_id)
#     if not reservation:
#         raise HTTPException(status_code=404, detail="Rezervace nenalezena")
#
#     # zákazník vidí jen své rezervace
#     if current_user["role_id"] == ROLE_CUSTOMER and reservation["user_id"] != current_user["id"]:
#         raise HTTPException(status_code=403, detail="Nemáte přístup k této rezervaci")
#
#     statuses = status_svc.list_statuses()
#     flags = _profile_role_flags(current_user)
#
#     tpl = request.app.state.templates
#     return tpl.TemplateResponse(
#         "reservations/reservation_detail.html",
#         {
#             "request": request,
#             "title": f"Rezervace {reservation['code']}",
#             "reservation": reservation,
#             "statuses": statuses,
#             "current_user": current_user,
#             **flags,
#         },
#     )

@router.get("/{reservation_id}", name="reservation_detail")
async def reservation_detail(
    reservation_id: int,
    request: Request,
    svc: ReservationService = Depends(reservation_service),
    status_svc: ReservationStatusService = Depends(reservation_status_service),
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    reservation = svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    # zákazník vidí jen své rezervace
    if current_user["role_id"] == ROLE_CUSTOMER and reservation["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Nemáte přístup k této rezervaci")

    # --- tady nově načteme položky rezervace (pokoje) ---
    try:
        items: List[Dict[str, Any]] = res_item_svc.list_items_by_reservation(
            reservation_id=reservation_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        # třeba kdyby rezervace neexistovala – ale to už mám nahoře, takže spíš fallback
        items = []

    statuses = status_svc.list_statuses()
    flags = _profile_role_flags(current_user)

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_detail.html",
        {
            "request": request,
            "title": f"Rezervace {reservation['code']}",
            "reservation": reservation,
            "items": items,
            "statuses": statuses,
            "current_user": current_user,
            **flags,
        },
    )

@router.post("/{reservation_id}/status", name="reservation_update_status")
async def reservation_update_status(
    reservation_id: int,
    request: Request,
    new_status_id: int = Form(...),
    svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    current_user_id = current_user["id"]
    current_user_role = current_user["role_id"]

    try:
        svc.update_reservation_status(
            reservation_id=reservation_id,
            new_status_id=new_status_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("reservation_detail", reservation_id=reservation_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )
