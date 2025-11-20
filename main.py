from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from pages.AuthPage import router as auth_router
from pages.BookingPage import router as booking_router
from pages.PaymentPage import router as payment_router
from pages.ReservationPage import router as reservation_router
from pages.UserPage import router as user_router
from pages.RoomPage import router as room_router

def create_app() -> FastAPI:
    app = FastAPI(title="Mini FastAPI – Hotel")
    app.state.templates = Jinja2Templates(directory="templates")

    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(booking_router, prefix="/bookings", tags=["bookings"])
    app.include_router(payment_router, prefix="/payments", tags=["payments"])
    app.include_router(reservation_router, prefix="/reservations", tags=["reservations"])
    app.include_router(user_router, prefix="/users", tags=["users"])
    app.include_router(room_router, prefix="/rooms", tags=["rooms"])
    return app

app = create_app()
