from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from pages.AuthPage import router as auth_router
from pages.BookingPage import router as booking_router  # ← nový import

def create_app() -> FastAPI:
    app = FastAPI(title="Mini FastAPI – Hotel")
    app.state.templates = Jinja2Templates(directory="templates")

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(booking_router, prefix="/bookings", tags=["bookings"])

    return app

app = create_app()
