from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse

from services.ContactMessageService import ContactMessageService
from dependencies import contact_message_service
from auth_dependencies import get_current_user
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER

router = APIRouter()


@router.get("/profile/messages", name="contact_messages_list")
async def contact_messages_list(
    request: Request,
    name: Optional[str] = Query(None, description="Filtrování podle jména odesílatele"),
    msg_svc: ContactMessageService = Depends(contact_message_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]

    is_admin = role_id == ROLE_ADMIN
    is_receptionist = role_id == ROLE_RECEPTIONIST
    is_customer = role_id == ROLE_CUSTOMER

    try:
        messages: List[Dict[str, Any]] = msg_svc.list_contact_messages(current_user_role=role_id, name=name)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_contact_messages.html",
        {
            "request": request,
            "title": "Přijaté zprávy",
            "current_user": current_user,
            "is_admin": is_admin,
            "is_receptionist": is_receptionist,
            "is_customer": is_customer,
            "contact_messages": messages,
            "filter_name": name or "",
        },
    )


@router.get("/profile/messages/{msg_id}", name="contact_message_detail")
async def contact_message_detail(
    msg_id: int,
    request: Request,
    msg_svc: ContactMessageService = Depends(contact_message_service),
    current_user = Depends(get_current_user),
):
    if isinstance(current_user, RedirectResponse):
        return current_user

    role_id = current_user["role_id"]

    if role_id not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
        raise HTTPException(status_code=403, detail="Nemáte oprávnění zobrazit detail zprávy")

    message = msg_svc.get_contact_message_by_id(msg_id)
    if not message:
        raise HTTPException(status_code=404, detail="Zpráva nenalezena")

    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "profile/profile_contact_message_detail.html",
        {
            "request": request,
            "title": f"Zpráva #{message['id']}",
            "current_user": current_user,
            "message": message,
        },
    )

