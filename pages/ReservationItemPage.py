from typing import List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse

from services.ReservationItemService import ReservationItemService
from services.ReservationService import ReservationService
from services.RoomService import RoomService

from dependencies import reservation_item_service, reservation_service, room_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST

router = APIRouter()


@router.get("/reservations/{reservation_id}/items", name="reservation_items_list")
async def reservation_items_list(
    reservation_id: int,
    request: Request,
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    reservation_svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    # hlavička rezervace
    reservation = reservation_svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

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

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_items_list.html",  # uprav si název šablony podle toho, co vytvoříš
        {
            "request": request,
            "title": f"Položky rezervace {reservation['code']}",
            "reservation": reservation,
            "items": items,
            "current_user": current_user,
            "is_admin_or_receptionist": current_user["role_id"] in (ROLE_ADMIN, ROLE_RECEPTIONIST),
        },
    )


@router.post("/reservations/{reservation_id}/items", name="reservation_items_create")
async def reservation_items_create(
    reservation_id: int,
    request: Request,
    room_id: int = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    adults: int = Form(...),
    children: int = Form(0),
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    reservation_svc: ReservationService = Depends(reservation_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    reservation = reservation_svc.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Rezervace nenalezena")

    try:
        res_item_svc.create_reservation_item(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            reservation_id=reservation_id,  # hlavička rezervace
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("reservation_items_list", reservation_id=reservation_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/reservations/create", name="reservation_create_page")
def reservation_create_page(
    request: Request,
    check_in: str | None = None,
    check_out: str | None = None,
    adults: int = 1,
    children: int = 0,
    room_svc: RoomService = Depends(room_service),
    current_user = Depends(get_current_user),
):
    # nepřihlášený -> redirect na login (get_current_user to řeší)
    if isinstance(current_user, RedirectResponse):
        return current_user

    rooms: List[Dict[str, Any]] = []
    if check_in and check_out:
        rooms = room_svc.list_available_rooms(
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
        )

    search = {
        "check_in": check_in or "",
        "check_out": check_out or "",
        "adults": adults,
        "children": children,
    }

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "reservations/reservation_create.html",
        {
            "request": request,
            "rooms": rooms,
            "search": search,
            "current_user": current_user,
        },
    )
