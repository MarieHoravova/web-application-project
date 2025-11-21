import sqlite3
import random
import string
from typing import List, Dict, Any, Optional

from repositories.ReservationRepository import (
    get_reservation_by_id as repo_get_by_id,
    get_reservation_by_code as repo_get_by_code,
    list_reservations as repo_list_reservations,
    list_reservations_by_user as repo_list_reservations_by_user,
    create_reservation as repo_create_reservation,
    update_reservation_status as repo_update_reservation_status,
    update_reservation as repo_update_reservation,
    delete_reservation as repo_delete_reservation,
)

from domain.constants import (
    ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER,
    RESERVATION_STATUS_PENDING, RESERVATION_STATUS_CANCELLED
)


class ReservationService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ---- interní pomocná funkce na generování unikátního kódu ----
    def _generate_unique_code(self, length: int = 8) -> str:
        alphabet = string.ascii_uppercase + string.digits

        while True:
            code = "".join(random.choices(alphabet, k=length))
            existing = repo_get_by_code(self.conn, code)
            if not existing:
                return code

    # ---- CREATE (hlavička rezervace) ----
    def create_reservation(self, user_id: int) -> Dict[str, Any]:
        code = self._generate_unique_code()
        reservation = repo_create_reservation(
            self.conn,
            user_id=user_id,
            code=code,
            status_id=RESERVATION_STATUS_PENDING,
        )
        return reservation

    # ---- READ / LIST ----
    def list_reservations(self) -> List[Dict[str, Any]]:
        return repo_list_reservations(self.conn)

    def list_reservations_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        return repo_list_reservations_by_user(self.conn, user_id)

    def get_reservation_by_id(self, reservation_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(self.conn, reservation_id)

    # ---- STATUS CHANGE ----
    def update_reservation_status(
        self,
        reservation_id: int,
        new_status_id: int,
        current_user_id: int,
        current_user_role: int,
    ) -> Dict[str, Any]:
        """
        Změna statusu reservation s jednoduchými pravidly:
        - ADMIN/RECEPTIONIST: může nastavit jakýkoliv status
        - CUSTOMER:
            - může měnit pouze své vlastní reservation
            - může pouze CANCEL (např. status_id = RESERVATION_STATUS_CANCELLED)
        """
        reservation = repo_get_by_id(self.conn, reservation_id)
        if not reservation:
            raise ValueError("Reservation neexistuje")

        # Customer – smí jen své a jen cancel
        if current_user_role == ROLE_CUSTOMER:
            if reservation["user_id"] != current_user_id:
                raise PermissionError("Nemůžete měnit cizí rezervaci")
            if new_status_id != RESERVATION_STATUS_CANCELLED:
                raise PermissionError("Zákazník může změnit stav jen na 'cancelled'")

        # Admin / recepce – bez omezení (logiku můžeš zpřísnit později)
        updated = repo_update_reservation_status(self.conn, reservation_id, new_status_id)
        return updated

    # ---- ADMIN ONLY: update (uživatel / kód) ----
    def admin_update_reservation(
        self,
        reservation_id: int,
        current_user_role: int,
        user_id: Optional[int] = None,
        code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Speciální update reservation – jen pro admina nebo recepci.
        Umožňuje opravit user_id nebo code (např. chyba při zápisu).
        """
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění upravovat reservation")

        reservation = repo_get_by_id(self.conn, reservation_id)
        if not reservation:
            raise ValueError("Reservation neexistuje")

        updated = repo_update_reservation(self.conn, reservation_id, user_id=user_id, code=code)
        return updated

    # ---- DELETE jen ADMIN, RECEPČNÍ ----
    def delete_reservation(self, reservation_id: int, current_user_role: int) -> bool:
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění mazat rezervace")

        if not repo_get_by_id(self.conn, reservation_id):
            raise ValueError("Reservation neexistuje")

        repo_delete_reservation(self.conn, reservation_id)
        return True


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        service = ReservationService(conn)

        # --- PREP: smažu staré testovací RESERVATIONS a USERS korektně přes FK ---
        print("\n=== PREP: clean old test users & reservations ===")
        user_rows = conn.execute(
            "SELECT id FROM users WHERE email LIKE 'reservations_test_%'"
        ).fetchall()

        for u in user_rows:
            uid = u["id"]

            # nejdřív smažu položky z reservation_items navázané na reservation header daného usera
            conn.execute("""
                DELETE FROM reservation_items
                WHERE reservation_id IN (
                    SELECT id FROM reservations WHERE user_id = ?
                )
            """, (uid,))

            # smažu payments (i kdyby tam bylo ON DELETE CASCADE, nevadí)
            conn.execute("""
                DELETE FROM payments
                WHERE reservation_id IN (
                    SELECT id FROM reservations WHERE user_id = ?
                )
            """, (uid,))

            # smažu samotné reservations (hlavičky)
            conn.execute("DELETE FROM reservations WHERE user_id = ?", (uid,))

            # teprve pak smažu usera
            conn.execute("DELETE FROM users WHERE id = ?", (uid,))

        conn.commit()

        # --- vytvořím nového admina + customer ---
        print("\n=== PREP: create test users ===")
        cur1 = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("reservations_test_admin@example.com", "HASH", "Admin", "Tester", "123", ROLE_ADMIN))
        admin_id = cur1.lastrowid

        cur2 = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, ("reservations_test_customer@example.com", "HASH", "Cust", "Tester", "123", ROLE_CUSTOMER))
        customer_id = cur2.lastrowid

        conn.commit()

        # --- TEST: create_reservation ---
        print("\n=== TEST: create_reservation ===")
        b1 = service.create_reservation(user_id=customer_id)
        print("Created:", b1)
        reservation_id = b1["id"]

        print("\n=== TEST: get_reservation_by_id ===")
        print(service.get_reservation_by_id(reservation_id))

        print("\n=== TEST: list_reservations ===")
        print(service.list_reservations())

        print("\n=== TEST: list_reservations_by_user ===")
        print(service.list_reservations_by_user(customer_id))

        # ---- CUSTOMER STATUS CHANGE (valid) ----
        print("\n=== TEST: customer CANCEL reservation ===")
        updated = service.update_reservation_status(
            reservation_id=reservation_id,
            new_status_id=RESERVATION_STATUS_CANCELLED,
            current_user_id=customer_id,
            current_user_role=ROLE_CUSTOMER,
        )
        print("Cancelled:", updated)

        # ---- CUSTOMER STATUS CHANGE (invalid) ----
        print("\n=== TEST: customer tries CONFIRM reservation (should fail) ===")
        try:
            service.update_reservation_status(
                reservation_id=reservation_id,
                new_status_id=RESERVATION_STATUS_PENDING,  # něco jiného než cancel
                current_user_id=customer_id,
                current_user_role=ROLE_CUSTOMER,
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- CUSTOMER tries to change someone else’s reservation ----
        print("\n=== TEST: customer tries to modify foreign reservation (should fail) ===")
        try:
            service.update_reservation_status(
                reservation_id=reservation_id,
                new_status_id=RESERVATION_STATUS_CANCELLED,
                current_user_id=999,  # cizí
                current_user_role=ROLE_CUSTOMER,
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- ADMIN UPDATE reservations (code/user_id) ----
        print("\n=== TEST: admin_update_reservation ===")
        b2 = service.create_reservation(user_id=customer_id)
        updated_admin = service.admin_update_reservation(
            reservation_id=b2["id"],
            current_user_role=ROLE_ADMIN,
            user_id=admin_id,
            code="TEST_UPDATED",
        )
        print("Updated admin reservation:", updated_admin)

        # ---- CUSTOMER cannot admin-update ----
        print("\n=== TEST: customer tries admin_update_reservation (should fail) ===")
        try:
            service.admin_update_reservation(
                reservation_id=b2["id"],
                current_user_role=ROLE_CUSTOMER,
                user_id=customer_id,
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ---- DELETE reservation as admin ----
        print("\n=== TEST: delete_reservation as ADMIN ===")
        result = service.delete_reservation(b2["id"], current_user_role=ROLE_ADMIN)
        print("Deleted:", result)

        # ---- DELETE reservation as customer (should fail) ----
        print("\n=== TEST: delete_reservation as CUSTOMER (should fail) ===")
        try:
            service.delete_reservation(reservation_id, current_user_role=ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected PermissionError:", e)
