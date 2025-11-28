from fastapi import APIRouter, Request, Depends
from auth_dependencies import get_current_user_optional
router = APIRouter()

@router.get("/", name="home_page")
async def home_page(
    request: Request,
    current_user = Depends(get_current_user_optional),
):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "home/home.html",
        {
            "request": request,
            "title": "Domů",
            "current_user": current_user,
        },
    )

