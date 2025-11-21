from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from starlette import status

from services.ContactMessageService import ContactMessageService
from dependencies import contact_message_service

router = APIRouter()

@router.get("/contact", name="contact_page")
async def contact_page(request: Request, message_sent: bool = False):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "contact/contact.html",
        {
            "request": request,
            "title": "Kontakt",
            "message_sent": message_sent,
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
    # MARK: ukládání do db
    contact_svc.create_contact_message(name=name, email=email, message=message)

    # debug log
    print(f"[CONTACT] {name} <{email}>: {message}")

    # Tohle mám kvůli warningu na contact page
    url = request.url_for("contact_page")
    url = str(url) + "?message_sent=1" # nastavím flag, podle kterého šablona pozná, že se formulář úspěšně odeslal

    return RedirectResponse(
        url=url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
