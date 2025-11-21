from datetime import date
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.ReservationItemService import ReservationItemService
from services.ReservationService import ReservationService
from services.RoomService import RoomService

from dependencies import reservation_item_service, reservation_service, room_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

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
        "reservations/reservation_items_list.html",
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
            reservation_id=reservation_id,
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
    reservation_id: Optional[int] = None,
    room_svc: RoomService = Depends(room_service),
    reservation_svc: ReservationService = Depends(reservation_service),
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    rooms: List[Dict[str, Any]] = []
    nights: int = 0
    reservation: Optional[Dict[str, Any]] = None
    selected_items: List[Dict[str, Any]] = []

    if reservation_id is not None:
        reservation = reservation_svc.get_reservation_by_id(reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Rezervace nenalezena")
        try:
            selected_items = res_item_svc.list_items_by_reservation(
                reservation_id=reservation_id,
                current_user_id=current_user["id"],
                current_user_role=current_user["role_id"],
            )
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e))

    if check_in and check_out:
        rooms = room_svc.list_available_rooms(
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
        )

        try:
            d_in = date.fromisoformat(check_in)
            d_out = date.fromisoformat(check_out)
            nights = (d_out - d_in).days
            if nights < 0:
                nights = 0
        except ValueError:
            nights = 0

        rooms_with_prices: List[Dict[str, Any]] = []
        for room in rooms:
            base_price = room.get("base_price") or 0
            total_price = base_price * nights if nights > 0 else 0
            rooms_with_prices.append({
                **room,
                "price_per_night": base_price,
                "total_price": total_price,
                "nights": nights,
            })
        rooms = rooms_with_prices

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
            "nights": nights,
            "reservation": reservation,
            "selected_items": selected_items,
            "current_user": current_user,
        },
    )


@router.post("/reservations/select", name="reservation_select_room")
async def reservation_select_room(
    request: Request,
    room_id: int = Form(...),
    check_in: str = Form(...),
    check_out: str = Form(...),
    adults: int = Form(...),
    children: int = Form(0),
    reservation_id: Optional[int] = Form(None),
    reservation_svc: ReservationService = Depends(reservation_service),
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    # buď použijeme existující rezervaci, nebo založíme novou
    if reservation_id is None:
        reservation = reservation_svc.create_reservation(user_id=current_user["id"])
        reservation_id = reservation["id"]
    else:
        reservation = reservation_svc.get_reservation_by_id(reservation_id)
        if not reservation:
            raise HTTPException(status_code=404, detail="Rezervace nenalezena")
        if current_user["role_id"] == ROLE_CUSTOMER and reservation["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Nemáte přístup k této rezervaci")

    try:
        res_item_svc.create_reservation_item(
            room_id=room_id,
            check_in=check_in,
            check_out=check_out,
            adults=adults,
            children=children,
            reservation_id=reservation_id,
            current_user_id=current_user["id"],
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    redirect_url = f"{request.url_for('reservation_create_page')}?check_in={check_in}&check_out={check_out}&adults={adults}&children={children}&reservation_id={reservation_id}"

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/reservations/{reservation_id}/items/{item_id}/delete", name="reservation_item_delete")
async def reservation_item_delete(
    reservation_id: int,
    item_id: int,
    request: Request,
    res_item_svc: ReservationItemService = Depends(reservation_item_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    # načteme si položku, ať máme data pro návrat na create stránku
    item = res_item_svc.get_reservation_item_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Položka rezervace neexistuje")

    try:
        res_item_svc.delete_reservation_item(
            item_id=item_id,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # po smazání zůstaneme na reservation_create_page se stejnými parametry
    check_in = item["check_in"]
    check_out = item["check_out"]
    adults = item["adults"]
    children = item["children"]

    redirect_url = (
        f"{request.url_for('reservation_create_page')}"
        f"?check_in={check_in}"
        f"&check_out={check_out}"
        f"&adults={adults}"
        f"&children={children}"
        f"&reservation_id={reservation_id}"
    )

    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
