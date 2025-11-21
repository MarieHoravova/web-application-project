from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from starlette import status


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

@router.get("contact", name="contact_submit")
async def contact_submit(
        request: Request,
        name: str = Form(...),
        email: str = Form(...),
        message: str = Form(...),
):
    # MARK: ukládání do db
    print(f"[CONTACT] {name} <{email}>: {message}")
    url = request.url_for("contact_page")
    url = str(url) + "?message_sent=1"

    return RedirectResponse(
        url=url,
        status_code=status.HTTP_303_SEE_OTHER,
    )