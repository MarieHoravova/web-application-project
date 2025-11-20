from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/gallery", name="gallery_page")
async def gallery_page(request: Request):
    tpl = request.app.state.templates
    return tpl.TemplateResponse(
        "gallery/gallery.html",
        {
            "request": request,
            "title": "Galerie hotelu",
        },
    )
