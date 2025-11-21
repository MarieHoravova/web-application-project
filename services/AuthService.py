import sqlite3
from typing import Optional, Dict, Any

from core.security import hash_password, verify_password, create_access_token
from repositories.UserRepository import get_by_email as repo_get_by_email, get_by_id as get_user_by_id, create_user as repo_create_user, update_password as repo_update_password
from repositories.RoleRepository import get_by_id as repo_get_role_by_id
from models.Auth import RegisterRequest, ChangePasswordRequest

from domain.constants import ROLE_CUSTOMER


class AuthService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def login(self, email: str, password: str) -> str:
        user = repo_get_by_email(self.conn, email)

        if not user or not verify_password(password, user["password_hash"]):
            raise ValueError("Neplatné přihlášení")

        role = user["role_id"]

        token = create_access_token(sub=str(user["id"]), roles=[str(role)])
        return token

    def register(self, data: RegisterRequest) -> Dict[str, Any]:
        if repo_get_by_email(self.conn, data.email):
            raise ValueError("Uživatel s tímto emailem již existuje")

        hashed = hash_password(data.password)

        user = repo_create_user(
            self.conn,
            email=data.email,
            password_hash=hashed,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            role_id=ROLE_CUSTOMER
        )
        return user

    def change_password(self, user_id: int, data: ChangePasswordRequest):
        user = get_user_by_id(self.conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        if not verify_password(data.old_password, user["password_hash"]):
            raise ValueError("Neplatné staré heslo")

        new_hash = hash_password(data.new_password)
        repo_update_password(self.conn, user_id, new_hash)

        return True

    # Kvůli právům k jednotlivýcm stránkám
    def get_current_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        return get_user_by_id(self.conn, user_id)

# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        auth = AuthService(conn)

        # zajistí, že v tabulce roles existuje záznam s id=ROLE_CUSTOMER
        print(f"\n=== PREP: Ensure role exists (id={ROLE_CUSTOMER}, customer) ===")
        role = repo_get_role_by_id(conn, ROLE_CUSTOMER)
        if not role:
            conn.execute("INSERT INTO roles (id, description) VALUES (?, 'customer')", (ROLE_CUSTOMER,))
            conn.commit()
            print(f"Created role id={ROLE_CUSTOMER}")
        else:
            print(f"Role id={ROLE_CUSTOMER} OK")

        print("\n=== TEST: register (new user) ===")

        # nejdřív smažeme závislá data kvůli FOREIGN KEY constraintům
        conn.execute("""
            DELETE FROM payments
            WHERE booking_id IN (
                SELECT id FROM bookings
                WHERE user_id IN (SELECT id FROM users WHERE email = 'auth_test@example.com')
            )
        """)
        conn.execute("""
            DELETE FROM reservations
            WHERE booking_id IN (
                SELECT id FROM bookings
                WHERE user_id IN (SELECT id FROM users WHERE email = 'auth_test@example.com')
            )
        """)
        conn.execute("""
            DELETE FROM bookings
            WHERE user_id IN (SELECT id FROM users WHERE email = 'auth_test@example.com')
        """)
        conn.execute("DELETE FROM users WHERE email = 'auth_test@example.com'")
        conn.commit()

        req = RegisterRequest(
            email="auth_test@example.com",
            password="secret123",
            first_name="Auth",
            last_name="Tester",
            phone_number="123456789"
        )

        user = auth.register(req)
        print("Registered:", user)
        user_id = user["id"]

        print("\n=== TEST: login (correct password) ===")
        token = auth.login("auth_test@example.com", "secret123")
        print("Token:", token)

        print("\n=== TEST: login (incorrect password) ===")
        try:
            auth.login("auth_test@example.com", "WRONGPASS")
        except ValueError as e:
            print("Expected error:", e)

        print("\n=== TEST: get_current_user ===")
        print(auth.get_current_user(user_id))

        print("\n=== TEST: change_password ===")
        cp = ChangePasswordRequest(
            old_password="secret123",
            new_password="newpass456"
        )
        auth.change_password(user_id, cp)
        print("Password changed OK")

        print("\n=== TEST: login with old password (should fail) ===")
        try:
            auth.login("auth_test@example.com", "secret123")
        except ValueError as e:
            print("Expected error:", e)

        print("\n=== TEST: login with new password (should work) ===")
        token2 = auth.login("auth_test@example.com", "newpass456")
        print("Token:", token2)