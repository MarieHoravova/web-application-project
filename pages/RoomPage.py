from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends, Form, HTTPException, Query
from fastapi.responses import RedirectResponse
from starlette import status

from services.RoomService import RoomService
from services.RoomTypeService import RoomTypeService
from services.RoomStatusService import RoomStatusService
from dependencies import room_service, room_type_service, room_status_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

from repositories.ReservationItemRepository import (
    find_conflicting_reservations as repo_find_conflicts,
)

router = APIRouter()

def _profile_role_flags(current_user: dict) -> dict:
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
        "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
    }




@router.get("/", name="rooms_list")
async def rooms_list(
    request: Request,
    status_id: Optional[str] = Query(default=None),
    room_type_id: Optional[str] = Query(default=None),
    room_svc: RoomService = Depends(room_service),
    room_type_svc: RoomTypeService = Depends(room_type_service),
    room_status_svc: RoomStatusService = Depends(room_status_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    role_id = current_user["role_id"]

    if role_id not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit pokoje")

    # Zpracování parametrů filtru (převedení na int nebo None)
    filter_status_id: Optional[int] = None
    if status_id not in (None, ""):
        try:
            filter_status_id = int(status_id)
        except ValueError:
            pass

    filter_room_type_id: Optional[int] = None
    if room_type_id not in (None, ""):
        try:
            filter_room_type_id = int(room_type_id)
        except ValueError:
            pass

    # TADY JE TA ZMĚNA: Předáme filtry rovnou do servisu -> repozitáře -> SQL
    rooms: List[Dict[str, Any]] = room_svc.list_rooms(
        status_id=filter_status_id,
        room_type_id=filter_room_type_id
    )

    room_types = room_type_svc.list_room_types()
    statuses = room_status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "rooms/rooms_list.html",
        {
            "request": request,
            "title": "Seznam pokojů",
            "rooms": rooms,
            "room_types": room_types,
            "statuses": statuses,
            "filter_status_id": filter_status_id,
            "filter_room_type_id": filter_room_type_id,
            "current_user": current_user,
            **flags,
        },
    )

@router.get("/new", name="room_new")
async def room_new(
    request: Request,
    room_type_svc: RoomTypeService = Depends(room_type_service),
    room_status_svc: RoomStatusService = Depends(room_status_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]
    if role_id != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Pouze admin může vytvářet pokoje")

    room_types = room_type_svc.list_room_types()
    statuses = room_status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "rooms/room_new.html",
        {
            "request": request,
            "title": "Nový pokoj",
            "room_types": room_types,
            "statuses": statuses,
            "current_user": current_user,
            **_profile_role_flags(current_user),
        },
    )


@router.post("/", name="rooms_create")
async def rooms_create(
    request: Request,
    number: int = Form(...),
    room_type_id: int = Form(...),
    room_status_id: int = Form(...),
    image_path: str = Form(...),
    floor: int = Form(...),
    room_svc: RoomService = Depends(room_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]
    if role_id != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Pouze admin může vytvářet pokoje")

    try:
        room_svc.create_room(
            number=number,
            room_type_id=room_type_id,
            room_status_id=room_status_id,
            image_path=image_path,
            floor=floor,
            current_user_role=role_id,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("rooms_list"),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get("/{room_id}", name="room_detail")
async def room_detail(
    room_id: int,
    request: Request,
    room_svc: RoomService = Depends(room_service),
    room_type_svc: RoomTypeService = Depends(room_type_service),
    room_status_svc: RoomStatusService = Depends(room_status_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    role_id = current_user["role_id"]
    if role_id not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit pokoje")

    room = room_svc.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Pokoj neexistuje")

    room_types = room_type_svc.list_room_types()
    statuses = room_status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "rooms/room_detail.html",
        {
            "request": request,
            "title": f"Pokoj {room['number']}",
            "room": room,
            "room_types": room_types,
            "statuses": statuses,
            "current_user": current_user,
            **flags,
        },
    )


@router.get("/{room_id}/edit", name="room_edit")
async def room_edit(
    room_id: int,
    request: Request,
    room_svc: RoomService = Depends(room_service),
    room_type_svc: RoomTypeService = Depends(room_type_service),
    room_status_svc: RoomStatusService = Depends(room_status_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    role_id = current_user["role_id"]
    if role_id not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat pokoje")

    room = room_svc.get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Pokoj neexistuje")

    room_types = room_type_svc.list_room_types()
    statuses = room_status_svc.list_statuses()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "rooms/room_edit.html",
        {
            "request": request,
            "title": f"Upravit pokoj {room['number']}",
            "room": room,
            "room_types": room_types,
            "statuses": statuses,
            "current_user": current_user,
            **flags,
        },
    )


@router.post("/{room_id}", name="room_update")
async def room_update(
    room_id: int,
    request: Request,
    number: int = Form(...),
    room_type_id: int = Form(...),
    room_status_id: int = Form(...),
    image_path: str = Form(...),
    floor: int = Form(...),
    room_svc: RoomService = Depends(room_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]
    if role_id not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění upravovat pokoje")

    try:
        room_svc.update_room(
            room_id=room_id,
            current_user_role=role_id,
            number=number,
            room_type_id=room_type_id,
            room_status_id=room_status_id,
            image_path=image_path,
            floor=floor,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("room_detail", room_id=room_id),
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.post("/{room_id}/delete", name="room_delete")
async def room_delete(
    room_id: int,
    request: Request,
    room_svc: RoomService = Depends(room_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]
    if role_id != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Pouze admin může mazat pokoje")

    try:
        room_svc.delete_room(room_id, current_user_role=role_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("rooms_list"),
        status_code=status.HTTP_303_SEE_OTHER,
    )
