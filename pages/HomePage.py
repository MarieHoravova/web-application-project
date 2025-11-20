from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from starlette import status

router = APIRouter()


@router.get("/", name="home_page")
async def home_page(request: Request, message_sent: bool = False):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "home/home.html",
        {
            "request": request,
            "message_sent": message_sent,
        },
    )


@router.post("/contact", name="home_contact")
async def home_contact(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    message: str = Form(...),
):
    # Tady případně později napojíš email / uložení do DB atd.
    print(f"[CONTACT] {name} <{email}>: {message}")

    url = request.url_for("home_page")
    url = str(url) + "?message_sent=1"

    return RedirectResponse(
        url=url,
        status_code=status.HTTP_303_SEE_OTHER,
    )
