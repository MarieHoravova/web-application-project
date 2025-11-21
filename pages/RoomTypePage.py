from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse

from services.RoomTypeService import RoomTypeService
from dependencies import room_type_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

router = APIRouter()


def _profile_role_flags(current_user: dict) -> dict:
    role_id = current_user["role_id"]
    return {
        "is_admin": role_id == ROLE_ADMIN,
        "is_receptionist": role_id == ROLE_RECEPTIONIST,
        "is_customer": role_id == ROLE_CUSTOMER,
        "is_admin_or_receptionist": role_id in (ROLE_ADMIN, ROLE_RECEPTIONIST),
    }


@router.get("/types", name="room_types_list")
async def room_types_list(
    request: Request,
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)

    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="Pouze admin může spravovat typy pokojů")

    room_types = room_type_svc.list_room_types()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "room_types/room_types_list.html",
        {
            "request": request,
            "title": "Typy pokojů",
            "room_types": room_types,
            "current_user": current_user,
            **flags,
        },
    )


@router.get("/types/new", name="room_type_new")
async def room_type_new(
    request: Request,
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="Pouze admin může spravovat typy pokojů")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "room_types/room_type_new.html",
        {
            "request": request,
            "title": "Nový typ pokoje",
            "current_user": current_user,
            **flags,
        },
    )


@router.post("/", name="room_types_create")
async def room_types_create(
    request: Request,
    name: str = Form(...),
    capacity: int = Form(...),
    base_price: float = Form(...),
    description: Optional[str] = Form(None),
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="Pouze admin může spravovat typy pokojů")

    try:
        room_type_svc.create_room_type(
            name=name,
            capacity=capacity,
            base_price=base_price,
            description=description,
            current_user_role=current_user["role_id"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(
        url=request.url_for("room_types_list"),
        status_code=303,
    )


@router.get("/{room_type_id}", name="room_type_detail")
async def room_type_detail(
    room_type_id: int,
    request: Request,
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    if not flags["is_admin_or_receptionist"]:
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit typy pokojů")

    room_type = room_type_svc.get_room_type_by_id(room_type_id)
    if not room_type:
        raise HTTPException(status_code=404, detail="Typ pokoje neexistuje")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "room_types/room_type_detail.html",
        {
            "request": request,
            "title": f"Typ pokoje: {room_type['name']}",
            "room_type": room_type,
            "current_user": current_user,
            **flags,
        },
    )


@router.get("/{room_type_id}/edit", name="room_type_edit")
async def room_type_edit(
    room_type_id: int,
    request: Request,
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="Pouze admin může spravovat typy pokojů")

    room_type = room_type_svc.get_room_type_by_id(room_type_id)
    if not room_type:
        raise HTTPException(status_code=404, detail="Typ pokoje neexistuje")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "room_types/room_type_edit.html",
        {
            "request": request,
            "title": f"Upravit typ pokoje {room_type['name']}",
            "room_type": room_type,
            "current_user": current_user,
            **flags,
        },
    )


@router.post("/{room_type_id}", name="room_type_update")
async def room_type_update(
    room_type_id: int,
    request: Request,
    name: str = Form(...),
    capacity: int = Form(...),
    base_price: float = Form(...),
    description: Optional[str] = Form(None),
    room_type_svc: RoomTypeService = Depends(room_type_service),
    current_user=Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    flags = _profile_role_flags(current_user)
    if not flags["is_admin"]:
        raise HTTPException(status_code=403, detail="Pouze admin může spravovat typy pokojů")

    try:
        room_type_svc.update_room_type(
            room_type_id=room_type_id,
            current_user_role=current_user["role_id"],
            name=name,
            capacity=capacity,
            base_price=base_price,
            description=description,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return RedirectResponse(
        url=request.url_for("room_types_list"),
        status_code=303,
    )
