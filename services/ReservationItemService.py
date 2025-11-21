# services/ReservationItemService.py
import sqlite3
from typing import List, Dict, Any

from repositories.ReservationItemRepository import (
    get_reservation_item_by_id as repo_get_item_by_id,
    list_reservation_items_by_reservation as repo_list_items_by_reservation,
    list_reservation_items_by_room as repo_list_items_by_room,
    create_reservation_item as repo_create_item,
    delete_reservation_item as repo_delete_item,
    find_conflicting_reservation_items as repo_find_conflicts,
    list_reservation_items_in_period as repo_list_items_in_period,
)

from repositories.ReservationRepository import (
    get_reservation_by_id as repo_get_reservation_by_id,
)

from repositories.RoomRepository import (
    get_room_by_id as repo_get_room_by_id,
)

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


class ReservationItemService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_reservation_item_by_id(self, item_id: int) -> Dict[str, Any] | None:
        return repo_get_item_by_id(self.conn, item_id)

    # ---- LIST položek podle rezervace ----
    def list_items_by_reservation(self, reservation_id: int, current_user_id: int, current_user_role: int) -> List[Dict[str, Any]]:
        reservation = repo_get_reservation_by_id(self.conn, reservation_id)
        if not reservation:
            raise ValueError("Rezervace neexistuje")

        if current_user_role == ROLE_CUSTOMER and reservation["user_id"] != current_user_id:
            raise PermissionError("Nemůžete zobrazit rezervace jiného uživatele")

        return repo_list_items_by_reservation(self.conn, reservation_id)

    # ---- LIST položek podle pokoje ----
    def list_items_by_room(self, room_id: int, current_user_role: int) -> List[Dict[str, Any]]:
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Pouze admin nebo recepce může zobrazit rezervace podle pokoje")

        return repo_list_items_by_room(self.conn, room_id)

    # ---- CREATE položky rezervace ----
    def create_reservation_item(
        self,
        room_id: int,
        check_in: str,
        check_out: str,
        adults: int,
        children: int,
        reservation_id: int,
        current_user_id: int,
        current_user_role: int,
    ) -> Dict[str, Any]:
        room = repo_get_room_by_id(self.conn, room_id)
        if not room:
            raise ValueError("Pokoj neexistuje")

        reservation = repo_get_reservation_by_id(self.conn, reservation_id)
        if not reservation:
            raise ValueError("Rezervace neexistuje")

        if current_user_role == ROLE_CUSTOMER and reservation["user_id"] != current_user_id:
            raise PermissionError("Nemůžete vytvořit položku do cizí rezervace")

        conflicts = repo_find_conflicts(self.conn, room_id, check_in, check_out)
        if conflicts:
            raise ValueError("Termín se překrývá s jinou rezervací")

        return repo_create_item(self.conn, room_id, check_in, check_out, adults, children, reservation_id)

    # ---- DELETE položky rezervace ----
    def delete_reservation_item(self, item_id: int, current_user_role: int) -> bool:
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Pouze admin nebo recepce může mazat položky rezervace")

        item = repo_get_item_by_id(self.conn, item_id)
        if not item:
            raise ValueError("Položka rezervace neexistuje")

        repo_delete_item(self.conn, item_id)
        return True

    # ---- Přehled obsazenosti v období (položky) ----
    def list_items_in_period(self, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        return repo_list_items_in_period(self.conn, date_from, date_to)


if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        service = ReservationItemService(conn)

        print("\n=== PREP: cleaning old reservations, reservation_items and users ===")

        old_users = conn.execute("SELECT id FROM users WHERE email LIKE 'res_test_%'").fetchall()
        for u in old_users:
            uid = u["id"]

            # Nejdřív SMAZAT položky z reservation_items podle rezervací daného usera
            conn.execute("""
                DELETE FROM reservation_items
                WHERE reservation_id IN (SELECT id FROM reservations WHERE user_id = ?)
            """, (uid,))

            # Pak smažu samotné rezervace
            conn.execute("DELETE FROM reservations WHERE user_id = ?", (uid,))

            # A nakonec usera
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))

        # Mazání test pokoje
        conn.execute("DELETE FROM rooms WHERE number = 777")
        conn.commit()

        print("\n=== PREP: creating test admin, customer, room, reservation ===")

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

        reservation_id = conn.execute("""
            INSERT INTO reservations (user_id, code, status_id, created_at)
            VALUES (?, 'RESTEST', 1, datetime('now'))
        """, (customer_id,)).lastrowid

        conn.commit()

        print("Admin ID:", admin_id)
        print("Customer ID:", customer_id)
        print("Room ID:", room_id)
        print("reservation ID:", reservation_id)

        print("\n=== TEST 1: create_reservation_item (valid) ===")
        r1 = service.create_reservation_item(
            room_id=room_id,
            check_in="2025-02-01",
            check_out="2025-02-05",
            adults=2,
            children=0,
            reservation_id=reservation_id,
            current_user_id=customer_id,
            current_user_role=ROLE_CUSTOMER,
        )
        print("Created:", r1)
        r1_id = r1["id"]

        print("\n=== TEST 2: list_items_by_reservation (customer OK) ===")
        print(service.list_items_by_reservation(reservation_id, customer_id, ROLE_CUSTOMER))

        print("\n=== TEST 3: customer tries to read someone else's reservation (FAIL) ===")
        try:
            service.list_items_by_reservation(reservation_id, 999, ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected error:", e)

        print("\n=== TEST 4: creating conflicting reservation_item (should FAIL) ===")
        try:
            service.create_reservation_item(
                room_id=room_id,
                check_in="2025-02-03",
                check_out="2025-02-06",
                adults=2,
                children=0,
                reservation_id=reservation_id,
                current_user_id=customer_id,
                current_user_role=ROLE_CUSTOMER,
            )
        except ValueError as e:
            print("Expected conflict:", e)

        print("\n=== TEST 5: admin deletes reservation_item (OK) ===")
        deleted = service.delete_reservation_item(r1_id, ROLE_ADMIN)
        print("Deleted:", deleted)

        print("\n=== TEST 6: customer tries to delete reservation_item (FAIL) ===")
        try:
            service.delete_reservation_item(r1_id, ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected:", e)
