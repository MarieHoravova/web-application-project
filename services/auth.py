import sqlite3
from typing import Optional, Dict

from core.security import hash_password, verify_password, create_access_token
from repositories.UserRepository import get_by_email, get_by_id, create_user, update_user
from repositories.RoleRepository import get_by_id as get_role_by_id
from models.Auth import RegisterRequest, ChangePasswordRequest

class AuthService:
    def login(self, conn: sqlite3.Connection, email: str, password: str) -> str:
        user = get_by_email(conn, email)

        if not user or not verify_password(password, user["password_hash"]):
            raise ValueError("Neplatné přihlášení")

        role = user["role_id"]

        token = create_access_token(sub=str(user["id"]), roles=[str(role)])
        return token

    def register(self, conn: sqlite3.Connection, data: RegisterRequest) -> Dict[str, any]:
        if get_by_email(conn, data.email):
            raise ValueError("Uživatel s tímto emailem již existuje")

        DEFAULT_ROLE_CUSTOMER = 3

        hashed = hash_password(data.password)

        user = create_user(
            conn,
            email=data.email,
            password_hash=hashed,
            first_name=data.first_name,
            last_name=data.last_name,
            phone_number=data.phone_number,
            role_id=DEFAULT_ROLE_CUSTOMER
        )
        return user

    def change_password(self, conn: sqlite3.Connection, user_id: int, data: ChangePasswordRequest):
        user = get_by_id(conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        if not verify_password(data.old_password, user["password_hash"]):
            raise ValueError("Neplatné staré heslo")

        new_hash = hash_password(data.new_password)

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_hash, user_id)
        )
        conn.commit()

        return True

    def get_current_user(self, conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, any]]:
        return get_by_id(conn, user_id)

# TEST
if __name__ == "__main__":
    from database.database import open_connection
    auth = AuthService()

    with open_connection() as conn:
        print("\n=== PREP: Ensure role exists (id=3) ===")
        role = get_role_by_id(conn, 3)
        if not role:
            conn.execute("INSERT INTO roles (description) VALUES ('user')")
            conn.commit()
            print("Created role id=3")
        else:
            print("Role id=3 OK")

        print("\n=== TEST: register (new user) ===")
        conn.execute("DELETE FROM users WHERE email = 'auth_test@example.com'")
        conn.commit()

        req = RegisterRequest(
            email="auth_test@example.com",
            password="secret123",
            first_name="Auth",
            last_name="Tester",
            phone_number="123456789"
        )

        user = auth.register(conn, req)
        print("Registered:", user)
        user_id = user["id"]

        print("\n=== TEST: login (correct password) ===")
        token = auth.login(conn, "auth_test@example.com", "secret123")
        print("Token:", token)

        print("\n=== TEST: login (incorrect password) ===")
        try:
            auth.login(conn, "auth_test@example.com", "WRONGPASS")
        except ValueError as e:
            print("Expected error:", e)

        print("\n=== TEST: get_current_user ===")
        print(auth.get_current_user(conn, user_id))

        print("\n=== TEST: change_password ===")
        cp = ChangePasswordRequest(
            old_password="secret123",
            new_password="newpass456"
        )
        auth.change_password(conn, user_id, cp)
        print("Password changed OK")

        print("\n=== TEST: login with old password (should fail) ===")
        try:
            auth.login(conn, "auth_test@example.com", "secret123")
        except ValueError as e:
            print("Expected error:", e)

        print("\n=== TEST: login with new password (should work) ===")
        token2 = auth.login(conn, "auth_test@example.com", "newpass456")
        print("Token:", token2)
