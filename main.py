from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from pages.HomePage import router as home_router
from pages.AuthPage import router as auth_router
from pages.BookingPage import router as booking_router
from pages.PaymentPage import router as payment_router
from pages.ReservationPage import router as reservation_router
from pages.UserPage import router as user_router
from pages.RoomPage import router as room_router
from pages.PublicRoomsPage import router as public_rooms_router
from pages.ProfilePage import router as profile_router
from pages.GalleryPage import router as gallery_router
from pages.ContactPage import router as contact_router
from pages.ContactAdminPage import router as contact_admin_router


def create_app() -> FastAPI:
    app = FastAPI(title="Mini FastAPI – Hotel")
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.state.templates = Jinja2Templates(directory="templates")

    app.include_router(home_router)
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
    app.include_router(booking_router, prefix="/bookings", tags=["bookings"])
    app.include_router(payment_router, prefix="/payments", tags=["payments"])
    app.include_router(reservation_router, prefix="/reservations", tags=["reservations"])
    app.include_router(user_router, prefix="/users", tags=["users"])
    app.include_router(room_router, prefix="/rooms", tags=["rooms"])

    app.include_router(public_rooms_router)
    app.include_router(profile_router)
    app.include_router(gallery_router)
    app.include_router(contact_router)
    app.include_router(contact_admin_router)
    return app



# request v kontextu šablony → Jinja potřebuje request, aby mohla pracovat s URL, query parametry atd.
# request.url_for("contact_page") → podle názvu routy složí správnou URL.

app = create_app()
