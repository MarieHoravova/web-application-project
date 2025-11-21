from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/", name="home_page")
async def home_page(request: Request):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "home/home.html",
        {
            "request": request,
        },
    )

