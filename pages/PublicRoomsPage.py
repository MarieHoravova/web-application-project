from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Request, Depends

from services.RoomService import RoomService
from services.RoomTypeService import RoomTypeService
from dependencies import room_service, room_type_service

router = APIRouter()


@router.get("/rooms", name="public_rooms_list")
async def public_rooms_list(
    request: Request,
    room_type_id: Optional[int] = None,
    room_svc: RoomService = Depends(room_service),
    room_type_svc: RoomTypeService = Depends(room_type_service),
):
    # pokud je vybraný typ, filtrujeme, jinak všechny
    if room_type_id is not None:
        rooms: List[Dict[str, Any]] = room_svc.list_rooms_by_type(room_type_id)
    else:
        rooms = room_svc.list_rooms()

    room_types = room_type_svc.list_room_types()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "public/rooms_list.html",
        {
            "request": request,
            "title": "Pokoje",
            "rooms": rooms,
            "room_types": room_types,
            "filter_room_type_id": room_type_id,
        },
    )
