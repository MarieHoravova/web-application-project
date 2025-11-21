import sqlite3
from typing import List, Dict, Any, Optional
from models.Payment import PaymentCreate

from repositories.PaymentRepository import (
    get_payment_by_id as repo_get_payment_by_id,
    list_all_payments as repo_list_all,
    list_payments_by_booking as repo_list_by_booking,
    create_payment as repo_create_payment,
    delete_payment as repo_delete_payment,
)
from repositories.ReservationRepository import (
    get_reservation_by_id as repo_get_booking_by_id,
)
from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


class PaymentService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_payment_by_id(self, payment_id: int):
        return repo_get_payment_by_id(self.conn, payment_id)

    # ---- LIST ALL (ADMIN / RECEPCE) ----
    def list_all_payments(self, current_user_role: int):
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění zobrazit všechny platby")
        return repo_list_all(self.conn)

    # ---- LIST BY BOOKING (práva podle role) ----
    def list_payments_by_booking(
        self,
        booking_id: int,
        current_user_id: int,
        current_user_role: int
    ) -> List[Dict[str, Any]]:

        booking = repo_get_booking_by_id(self.conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        # CUSTOMER: může jen platby svých bookingů
        if current_user_role == ROLE_CUSTOMER:
            if booking["user_id"] != current_user_id:
                raise PermissionError("Nemůžete zobrazit platby cizího bookingU")

        # ADMIN / RECEPCE: mohou všechno
        return repo_list_by_booking(self.conn, booking_id)

    # ---- CREATE PAYMENT (jen ADMIN/RECEPCE) ----
    def create_payment(
        self,
        booking_id: int,
        amount: float,
        method_id: int,
        current_user_role: int
    ) -> Dict[str, Any]:

        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění vytvářet platby")
        booking = repo_get_booking_by_id(self.conn, booking_id)
        if not booking:
            raise ValueError("Booking neexistuje")

        return repo_create_payment(self.conn, booking_id, amount, method_id)

    # ---- DELETE PAYMENT (jen ADMIN) ----
    def delete_payment(
        self,
        payment_id: int,
        current_user_role: int
    ) -> bool:

        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Platby může mazat pouze admin")

        payment = repo_get_payment_by_id(self.conn, payment_id)
        if not payment:
            raise ValueError("Platba neexistuje")

        repo_delete_payment(self.conn, payment_id)
        return True


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        service = PaymentService(conn)

        print("\n=== PREP: clean test data ===")
        print("\n=== PREP: clean test data ===")

        # 1) Clean payments from test users
        conn.execute("""
                     DELETE
                     FROM payments
                     WHERE booking_id IN (SELECT id
                                          FROM bookings
                                          WHERE user_id IN (SELECT id
                                                            FROM users
                                                            WHERE email LIKE 'pay_%'))
                     """)

        # 2) Clean bookings
        conn.execute("""
                     DELETE
                     FROM bookings
                     WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'pay_%')
                     """)

        # 3) Clean users
        conn.execute("DELETE FROM users WHERE email LIKE 'pay_%'")

        # 4) Just to be sure: clean specific test payments
        conn.execute("DELETE FROM payments WHERE amount = 9999.0")

        conn.commit()

        # vytvoření admina i customer
        admin = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)
            VALUES ('pay_admin@example.com', 'X', 'Pay', 'Admin', ?, datetime('now'))
        """, (ROLE_ADMIN,)).lastrowid

        customer = conn.execute("""
            INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)
            VALUES ('pay_customer@example.com', 'X', 'Pay', 'Cust', ?, datetime('now'))
        """, (ROLE_CUSTOMER,)).lastrowid
        conn.commit()

        # booking pro customer
        booking = conn.execute("""
            INSERT INTO bookings (user_id, code, status_id, created_at)
            VALUES (?, 'PMTEST', 1, datetime('now'))
        """, (customer,)).lastrowid
        conn.commit()

        # payment method
        method = conn.execute("""
            INSERT INTO payment_methods (description)
            VALUES ('card')
        """).lastrowid
        conn.commit()

        print("\n=== TEST: create_payment as admin ===")
        p1 = service.create_payment(booking, 9999.0, method, ROLE_ADMIN)
        print("Created:", p1)

        print("\n=== TEST: list_payments_by_booking as customer (OK) ===")
        print(service.list_payments_by_booking(booking, customer, ROLE_CUSTOMER))

        print("\n=== TEST: list_payments_by_booking as someone else (FAIL) ===")
        try:
            service.list_payments_by_booking(booking, 999, ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected:", e)

        print("\n=== TEST: delete_payment as admin ===")
        result = service.delete_payment(p1["id"], ROLE_ADMIN)
        print("Deleted:", result)

        print("\n=== TEST: delete_payment as customer (FAIL) ===")
        try:
            service.delete_payment(p1["id"], ROLE_CUSTOMER)
        except PermissionError as e:
            print("Expected:", e)

