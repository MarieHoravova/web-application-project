import sqlite3
from typing import Iterator
from fastapi import Depends
from database.database import open_connection

from services.AuthService import AuthService
from services.BookingService import BookingService
from services.BookingStatusService import BookingStatusService
from services.PaymentMethodService import PaymentMethodService
from services.PaymentService import PaymentService
from services.ReservationService import ReservationService
from services.RoleService import RoleService
from services.RoomService import RoomService
from services.RoomStatusService import RoomStatusService
from services.RoomTypeService import RoomTypeService
from services.UserService import UserService


def get_conn() -> Iterator[sqlite3.Connection]:
    with open_connection() as conn:
        yield conn

def auth_service(conn: sqlite3.Connection = Depends(get_conn)) -> AuthService:
    return AuthService(conn)

def booking_service(conn: sqlite3.Connection = Depends(get_conn)) -> BookingService:
    return BookingService(conn)

def booking_status_service(conn: sqlite3.Connection = Depends(get_conn)) -> BookingStatusService:
    return BookingStatusService(conn)

def payment_method_service(conn: sqlite3.Connection = Depends(get_conn)) -> PaymentMethodService:
    return PaymentMethodService(conn)

def payment_service(conn: sqlite3.Connection = Depends(get_conn)) -> PaymentService:
    return PaymentService(conn)

def reservation_service(conn: sqlite3.Connection = Depends(get_conn)) -> ReservationService:
    return ReservationService(conn)

def role_service(conn: sqlite3.Connection = Depends(get_conn)) -> RoleService:
    return RoleService(conn)

def room_service(conn: sqlite3.Connection = Depends(get_conn)) -> RoomService:
    return RoomService(conn)

def room_status_service(conn: sqlite3.Connection = Depends(get_conn)) -> RoomStatusService:
    return RoomStatusService(conn)

def room_type_service(conn: sqlite3.Connection = Depends(get_conn)) -> RoomTypeService:
    return RoomTypeService(conn)

def user_service(conn: sqlite3.Connection = Depends(get_conn)) -> UserService:
    return UserService(conn)

