import sqlite3
import random
import string
from typing import List, Dict, Any, Optional

from repositories.BookingRepository import (
    get_booking_by_id as repo_get_by_id,
    get_booking_by_code as repo_get_by_code,
    list_bookings as repo_list_bookings,
    list_bookings_by_user as repo_list_bookings_by_user,
    create_booking as repo_create_booking,
    update_booking_status as repo_update_booking_status,
    update_booking as repo_update_booking,
    delete_booking as repo_delete_booking,
)

from domain.constants import (
    ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER,
    BOOKING_STATUS_PENDING, BOOKING_STATUS_CANCELLED
)


class BookingService:
    # ---- interní pomocná funkce na generování unikátního kódu ----
    def _generate_unique_code(self, conn: sqlite3.Connection, length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits

        while True:
            code = "".join(random.choices(alphabet, k=length))
            existing = repo_get_by_code(conn, code)
            if not existing:
                return code

    # ---- CREATE ----
    def create_booking(self, conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
        code = self._generate_unique_code(conn)
        booking = repo_create_booking(conn, user_id=user_id, code=code, status_id=BOOKING_STATUS_PENDING)
        return booking

    # ---- READ / LIST ----
    def list_bookings(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        return repo_list_bookings(conn)

    def list_bookings_by_user(self, conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
        return repo_list_bookings_by_user(conn, user_id)

    def get_booking_by_id(self, conn: sqlite3.Connection, booking_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(conn, booking_id)

    # ---- STATUS CHANGE ----
    def update_booking_status(self, conn: sqlite3.Connection, booking_id: int, new_status_id: int, current_user_id: int, current_user_role: int) -> Dict[str, Any]:
        """
        Změna statusu bookingu s jednoduchými pravidly:
        - ADMIN/RECEPTIONIST: může nastavit jakýkoliv status
        - CUSTOMER:
            - může měnit pouze své vlastní bookingy
            - může pouze CANCEL (např. status_id = 3)
        """
        booking = repo_get_by_id(conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        # Customer – smí jen své a jen cancel
        if current_user_role == ROLE_CUSTOMER:
            if booking["user_id"] != current_user_id:
                raise PermissionError("Nemůžete měnit cizí rezervaci")
            if new_status_id != BOOKING_STATUS_CANCELLED:
                raise PermissionError("Zákazník může změnit stav jen na 'cancelled'")

        # Admin / recepce – bez omezení (logiku můžeš zpřísnit později)
        updated = repo_update_booking_status(conn, booking_id, new_status_id)
        return updated

    # ---- ADMIN ONLY: update (uživatel / kód) ----
    def admin_update_booking(self, conn: sqlite3.Connection, booking_id: int, current_user_role: int, user_id: Optional[int] = None, code: Optional[str] = None) -> Dict[str, Any]:
        """
        Speciální update bookingu – jen pro admina nebo recepci.
        Umožňuje opravit user_id nebo code (např. chyba při zápisu).
        """
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění upravovat booking")

        booking = repo_get_by_id(conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        updated = repo_update_booking(conn, booking_id, user_id=user_id, code=code)
        return updated

    # ---- DELETE jen ADMIN, RECEPČNÍ ----
    def delete_booking(self, conn, booking_id, current_user_role):
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění mazat bookingy")

        if not repo_get_by_id(conn, booking_id):
            raise ValueError("Booking neexistuje")

        repo_delete_booking(conn, booking_id)
        return True

# TEST
if __name__ == "__main__":
    from database.database import open_connection
    from domain.constants import (
        ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER,
        BOOKING_STATUS_PENDING, BOOKING_STATUS_CANCELLED
    )

    service = BookingService()

    with open_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # --- PREP: smažu staré testovací BOOKINGY a USERS korektně přes FK ---
        print("\n=== PREP: clean old test users & bookings ===")
        user_rows = conn.execute(
            "SELECT id FROM users WHERE email LIKE 'booking_test_%'"
        ).fetchall()

        for u in user_rows:
            uid = u["id"]
            # nejdřív smažu reservations navázané na bookingy toho usera
            conn.execute("""
                DELETE FROM reservations
                WHERE booking_id IN (
                    SELECT id FROM bookings WHERE user_id = ?
                )
            """, (uid,))
            # smažu payments (i kdyby tam bylo ON DELETE CASCADE, nevadí)
            conn.execute("""
                DELETE FROM payments
                WHERE booking_id IN (
                    SELECT id FROM bookings WHERE user_id = ?
                )
            """, (uid,))
            # smažu samotné bookings
            conn.execute("DELETE FROM bookings WHERE user_id = ?", (uid,))
            # teprve pak smažu usera
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))

        conn.commit()

        # --- vytvořím nového admina + customer ---
        print("\n=== PREP: create test users ===")
        cur1 = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("booking_test_admin@example.com", "HASH", "Admin", "Tester", "123", ROLE_ADMIN))
        admin_id = cur1.lastrowid

        cur2 = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("booking_test_customer@example.com", "HASH", "Cust", "Tester", "123", ROLE_CUSTOMER))
        customer_id = cur2.lastrowid

        conn.commit()

        # --- TEST: create_booking ---
        print("\n=== TEST: create_booking ===")
        b1 = service.create_booking(conn, user_id=customer_id)
        print("Created:", b1)
        booking_id = b1["id"]

        print("\n=== TEST: get_booking_by_id ===")
        print(service.get_booking_by_id(conn, booking_id))

        print("\n=== TEST: list_bookings ===")
        print(service.list_bookings(conn))

        print("\n=== TEST: list_bookings_by_user ===")
        print(service.list_bookings_by_user(conn, customer_id))

        # ---- CUSTOMER STATUS CHANGE (valid) ----
        print("\n=== TEST: customer CANCEL booking ===")
        updated = service.update_booking_status(
            conn,
            booking_id=booking_id,
            new_status_id=BOOKING_STATUS_CANCELLED,
            current_user_id=customer_id,
            current_user_role=ROLE_CUSTOMER
        )
        print("Cancelled:", updated)

        # ---- CUSTOMER STATUS CHANGE (invalid) ----
        print("\n=== TEST: customer tries CONFIRM booking (should fail) ===")
        try:
            service.update_booking_status(
                conn,
                booking_id=booking_id,
                new_status_id=BOOKING_STATUS_PENDING,  # něco jiného než cancel
                current_user_id=customer_id,
                current_user_role=ROLE_CUSTOMER
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- CUSTOMER tries to change someone else’s booking ----
        print("\n=== TEST: customer tries to modify foreign booking (should fail) ===")
        try:
            service.update_booking_status(
                conn,
                booking_id=booking_id,
                new_status_id=BOOKING_STATUS_CANCELLED,
                current_user_id=999,          # cizí
                current_user_role=ROLE_CUSTOMER
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- ADMIN UPDATE BOOKING (code/user_id) ----
        print("\n=== TEST: admin_update_booking ===")
        b2 = service.create_booking(conn, user_id=customer_id)
        updated_admin = service.admin_update_booking(
            conn,
            booking_id=b2["id"],
            current_user_role=ROLE_ADMIN,
            user_id=admin_id,
            code="TEST_UPDATED"
        )
        print("Updated admin booking:", updated_admin)

        # ---- CUSTOMER cannot admin-update ----
        print("\n=== TEST: customer tries admin_update_booking (should fail) ===")
        try:
            service.admin_update_booking(
                conn,
                booking_id=b2["id"],
                current_user_role=ROLE_CUSTOMER,
                user_id=customer_id
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- DELETE booking as admin ----
        print("\n=== TEST: delete_booking as ADMIN ===")
        result = service.delete_booking(conn, b2["id"], current_user_role=ROLE_ADMIN)
        print("Deleted:", result)

        # ---- DELETE booking as customer (should fail) ----
        print("\n=== TEST: delete_booking as CUSTOMER (should fail) ===")
        try:
            service.delete_booking(conn, booking_id, current_user_role=ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected PermissionError:", e)
