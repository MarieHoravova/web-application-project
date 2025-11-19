import sqlite3
from typing import List, Dict, Any, Optional

from repositories.ReservationRepository import (
    get_reservation_by_id as repo_get_by_id,
    list_reservations_by_booking as repo_list_by_booking,
    list_reservations_by_room as repo_list_by_room,
    create_reservation as repo_create_reservation,
    delete_reservation as repo_delete_reservation,
    find_conflicting_reservations as repo_find_conflicts,
)

from repositories.BookingRepository import (
    get_booking_by_id as repo_get_booking_by_id,
)

from repositories.RoomRepository import (
    get_room_by_id as repo_get_room_by_id,
)

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


class ReservationService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_reservation_by_id(self, reservation_id: int):
        return repo_get_by_id(self.conn, reservation_id)

    # ---- LIST ----
    def list_reservations_by_booking(self, booking_id: int, current_user_id: int, current_user_role: int):
        booking = repo_get_booking_by_id(self.conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        if current_user_role == ROLE_CUSTOMER and booking["user_id"] != current_user_id:
            raise PermissionError("Nemůžete zobrazit rezervace jiného uživatele")

        return repo_list_by_booking(self.conn, booking_id)

    def list_reservations_by_room(self, room_id: int, current_user_role: int):
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Pouze admin nebo recepce může zobrazit rezervace podle pokoje")

        return repo_list_by_room(self.conn, room_id)

    # ---- CREATE ----
    def create_reservation(self, room_id: int, check_in: str, check_out: str, adults: int, children: int, booking_id: int, current_user_id: int, current_user_role: int):
        room = repo_get_room_by_id(self.conn, room_id)
        if not room:
            raise ValueError("Pokoj neexistuje")

        booking = repo_get_booking_by_id(self.conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        if current_user_role == ROLE_CUSTOMER and booking["user_id"] != current_user_id:
            raise PermissionError("Nemůžete vytvořit rezervaci do cizího booking")

        # --- OVĚŘÍM, ZDA NEEXISTUJÍ KONFLIKTY --- #
        conflicts = repo_find_conflicts(self.conn, room_id, check_in, check_out)
        if conflicts:
            raise ValueError("Termín se překrývá s jinou rezervací")

        return repo_create_reservation(self.conn, room_id, check_in, check_out, adults, children, booking_id)

    # ---- DELETE ----
    def delete_reservation(self, reservation_id: int, current_user_role: int):
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Pouze admin nebo recepce může mazat rezervace")

        reservation = repo_get_by_id(self.conn, reservation_id)
        if not reservation:
            raise ValueError("Rezervace neexistuje")

        repo_delete_reservation(self.conn, reservation_id)
        return True


if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        service = ReservationService(conn)

        print("\n=== PREP: cleaning old reservations, bookings and users ===")

        old_users = conn.execute("SELECT id FROM users WHERE email LIKE 'res_test_%'").fetchall()
        for u in old_users:
            uid = u["id"]

            conn.execute("""
                         DELETE
                         FROM reservations
                         WHERE booking_id IN (SELECT id FROM bookings WHERE user_id = ?)
                         """, (uid,))

            conn.execute("DELETE FROM bookings WHERE user_id = ?", (uid,))
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))

        # Mazání test pokoje
        conn.execute("DELETE FROM rooms WHERE number = 777")

        conn.commit()

        print("\n=== PREP: creating test admin, customer, room, booking ===")

        admin_id = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)
            VALUES ('res_test_admin@example.com', 'X', 'Res', 'Admin', ?, datetime('now'))
        """, (ROLE_ADMIN,)).lastrowid

        customer_id = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)
            VALUES ('res_test_customer@example.com', 'X', 'Res', 'Cust', ?, datetime('now'))
        """, (ROLE_CUSTOMER,)).lastrowid

        conn.commit()

        room_id = conn.execute("""
            INSERT INTO rooms (number, room_type_id, room_status_id, image_path, floor)
            VALUES (777, 1, 1, 'test.jpg', 1)
        """).lastrowid

        booking_id = conn.execute("""
            INSERT INTO bookings (user_id, code, status_id, created_at)
            VALUES (?, 'RESTEST', 1, datetime('now'))
        """, (customer_id,)).lastrowid

        conn.commit()

        print("Admin ID:", admin_id)
        print("Customer ID:", customer_id)
        print("Room ID:", room_id)
        print("Booking ID:", booking_id)

        print("\n=== TEST 1: create_reservation (valid) ===")
        r1 = service.create_reservation(
            room_id=room_id,
            check_in="2025-02-01",
            check_out="2025-02-05",
            adults=2,
            children=0,
            booking_id=booking_id,
            current_user_id=customer_id,
            current_user_role=ROLE_CUSTOMER
        )
        print("Created:", r1)
        r1_id = r1["id"]

        print("\n=== TEST 2: list_reservations_by_booking (customer OK) ===")
        print(service.list_reservations_by_booking(booking_id, customer_id, ROLE_CUSTOMER))

        print("\n=== TEST 3: customer tries to read someone else's booking (FAIL) ===")
        try:
            service.list_reservations_by_booking(booking_id, 999, ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected error:", e)

        print("\n=== TEST 4: creating conflicting reservation (should FAIL) ===")
        try:
            service.create_reservation(
                room_id=room_id,
                check_in="2025-02-03",
                check_out="2025-02-06",
                adults=2,
                children=0,
                booking_id=booking_id,
                current_user_id=customer_id,
                current_user_role=ROLE_CUSTOMER
            )
        except ValueError as e:
            print("Expected conflict:", e)

        print("\n=== TEST 5: admin deletes reservation (OK) ===")
        deleted = service.delete_reservation(r1_id, ROLE_ADMIN)
        print("Deleted:", deleted)

        print("\n=== TEST 6: customer tries to delete reservation (FAIL) ===")
        try:
            service.delete_reservation(r1_id, ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected:", e)
