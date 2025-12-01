from fastapi import APIRouter, Request, Depends
from auth_dependencies import get_current_user_optional
from dependencies import room_type_service
from services.RoomTypeService import RoomTypeService

router = APIRouter()

@router.get("/gallery", name="gallery_page")
async def gallery_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
    rt_svc: RoomTypeService = Depends(room_type_service),
):
    rooms = rt_svc.list_room_types()

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "gallery/gallery.html",
        {
            "request": request,
            "title": "Galerie hotelu",
            "current_user": current_user,
            "rooms": rooms,
        },
    )
