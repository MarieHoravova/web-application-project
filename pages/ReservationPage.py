from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from starlette import status

from services.ReservationService import ReservationService
from services.ReservationStatusService import ReservationStatusService
from services.RoomService import RoomService
from dependencies import reservation_service, reservation_status_service, room_service
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
        user_id: Optional[str] = Query(default=None),  # Filtr ID
        user_name: Optional[str] = Query(default=None),  # Filtr Jméno
        svc: ReservationService = Depends(reservation_service),
        current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    current_user_id = current_user["id"]

    filter_user_id: Optional[int] = None
    filter_user_name: Optional[str] = None

    # ZÁKAZNÍK: Vidí jen své, filtry ignorujeme (nebo povolíme jen v rámci jeho rezervací)
    if flags["is_customer"]:
        # Natvrdo nastavíme filtr na jeho ID
        filter_user_id = current_user_id
        # Pokud by zákazník chtěl filtrovat své rezervace, můžeme tu logiku přidat,
        # ale zatím mu ukážeme prostě všechny jeho.
        reservations = svc.list_reservations(user_id=current_user_id)

    # ADMIN / RECEPCE: Může filtrovat podle čehokoliv
    else:
        # Zpracování ID
        if user_id not in (None, ""):
            try:
                filter_user_id = int(user_id)
            except ValueError:
                pass  # Chybný vstup ignorujeme

        # Zpracování Jména
        if user_name not in (None, ""):
            filter_user_name = user_name

        # Voláme servis s oběma filtry
        reservations = svc.list_reservations(
            user_id=filter_user_id,
            user_name=filter_user_name
        )

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_list.html",
        {
            "request": request,
            "title": "Seznam rezervací",
            "reservations": reservations,
            "filter_user_id": filter_user_id,
            "filter_user_name": filter_user_name,
            "current_user": current_user,
            **flags,
        },
    )

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



@router.get("/{reservation_id}/items/edit", name="reservation_items_edit_page")
async def reservation_items_edit_page(
    reservation_id: int,
    request: Request,
    reservation_svc: ReservationService = Depends(reservation_service),
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    room_svc: RoomService = Depends(room_service),
    current_user = Depends(get_current_user),
):
    # nepřihlášený → redirect na login (get_current_user vrací RedirectResponse)
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)

    # úprava pokojů jen pro admina / recepci
    if not flags["is_admin_or_receptionist"]:
        raise HTTPException(status_code=403, detail="Pouze admin nebo recepční mohou upravovat pokoje v rezervaci")

    # načteme rezervaci
    reservation = reservation_svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    # načteme položky rezervace (pokoje)
    try:
        items: List[Dict[str, Any]] = res_item_svc.list_items_by_reservation(
            reservation_id=reservation_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # volitelně – můžeš si tady nachystat i seznam všech pokojů,
    # pokud je chceš v šabloně rovnou nabídnout pro výměnu:
    rooms: List[Dict[str, Any]] = room_svc.list_rooms()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_items_edit.html",
        {
            "request": request,
            "title": f"Upravit pokoje v rezervaci {reservation['code']}",
            "reservation": reservation,
            "items": items,
            "rooms": rooms,
            "current_user": current_user,
            **flags,
        },
    )