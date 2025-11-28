from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from starlette import status

from services.ContactMessageService import ContactMessageService
from dependencies import contact_message_service
from auth_dependencies import get_current_user_optional
router = APIRouter()
# může (ale nemusí) dostat query parametr message_sent,
# když nepřijde = False, když přijde = zobrazí se alert "Děkujeme za zprávu...".
@router.get("/contact", name="contact_page")
async def contact_page(
    request: Request,
    message_sent: bool = False,
    current_user = Depends(get_current_user_optional),
):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "contact/contact.html",
        {
            "request": request,
            "title": "Kontakt",
            "message_sent": message_sent,
            "current_user": current_user,
        },
    )

@router.post("/contact", name="contact_submit")
async def contact_submit(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
    contact_svc: ContactMessageService = Depends(contact_message_service),
):
    contact_svc.create_contact_message(name=name, email=email, message=message)

    url = request.url_for("contact_page")
    url = str(url) + "?message_sent=1"

    return RedirectResponse(
        url=url,
        status_code=status.HTTP_303_SEE_OTHER,
    )