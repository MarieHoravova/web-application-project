import sqlite3
from typing import Optional, Dict, List

from repositories.UserRepository import (
    get_by_id as repo_get_by_id,
    get_by_email as repo_get_by_email,
    list_users as repo_list_users,
    list_users_by_role as repo_list_users_by_role,
    update_user as repo_update_user,
    delete_user as repo_delete_user,
    create_user as repo_create_user,)
from core.security import hash_password

from domain.constants import (
    ROLE_ADMIN, ROLE_CUSTOMER,
)


class UserService:
    # ADMIN: LIST USERS
    def list_users(self, conn: sqlite3.Connection) -> List[Dict[str, any]]:
        return repo_list_users(conn)

    def list_users_by_role(self, conn: sqlite3.Connection, role_id: int) -> List[Dict[str, any]]:
        return repo_list_users_by_role(conn, role_id)

    # ADMIN: CREATE USER (např. sekretářka)
    def create_user_admin(
        self,
        conn: sqlite3.Connection,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str],
        role_id: int
    ) -> Dict[str, any]:

        if repo_get_by_email(conn, email):
            raise ValueError("Uživatel s tímto emailem již existuje")

        pwd_hash = hash_password(password)

        return repo_create_user(
            conn,
            email=email,
            password_hash=pwd_hash,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role_id=role_id
        )

    # ADMIN: CHANGE USER ROLE
    def change_role(self, conn: sqlite3.Connection, user_id: int, role_id: int):
        user = repo_get_by_id(conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        return repo_update_user(conn, user_id, role_id=role_id)

    # ADMIN / USER: UPDATE PROFILE
    # (admin pro jiné, user pro sebe)
    def update_user_profile(
        self,
        conn: sqlite3.Connection,
        user_id: int,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ):
        user = repo_get_by_id(conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        return repo_update_user(
            conn,
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )

    # ADMIN: DELETE USER
    # - Customer může mazat jen sám sebe
    # - Admin (1) může mazat kohokoli
    def delete(self, conn: sqlite3.Connection, target_user_id: int, current_user_id: int, current_user_role: int):
        user = repo_get_by_id(conn, target_user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        # Pokud není admin, smí mazat jen sám sebe
        if current_user_role != ROLE_ADMIN and target_user_id != current_user_id:
            raise PermissionError("Nemáte oprávnění mazat tento účet")

        repo_delete_user(conn, target_user_id)
        return True


    # COMMON: GET USER
    def get_user_by_id(self, conn: sqlite3.Connection, user_id: int) -> Dict[str, any] | None:
        return repo_get_by_id(conn, user_id)


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    service = UserService()

    with open_connection() as conn:
        # ----- PREP: smažu staré testovací uživatele -----
        conn.execute("DELETE FROM users WHERE email LIKE 'test_user_%'")
        conn.commit()

        print("\n=== TEST: create_user_admin ===")
        u1 = service.create_user_admin(
            conn,
            email="test_user_1@example.com",
            password="secret123",
            first_name="Test",
            last_name="User1",
            phone_number="123456789",
            role_id= ROLE_ADMIN
        )
        print("Created:", u1)

        u2 = service.create_user_admin(
            conn,
            email="test_user_2@example.com",
            password="secret123",
            first_name="Test",
            last_name="User2",
            phone_number=None,
            role_id= ROLE_CUSTOMER
        )
        print("Created:", u2)

        # ----- LIST USERS -----
        print("\n=== TEST: list_users ===")
        print(service.list_users(conn))

        # ----- LIST USERS BY ROLE -----
        print("\n=== TEST: list_users_by_role (role 3) ===")
        print(service.list_users_by_role(conn, 3))

        # ----- GET USER -----
        print("\n=== TEST: get_user ===")
        print("Get u1:", service.get_user_by_id(conn, u1["id"]))

        # ----- UPDATE PROFILE -----
        print("\n=== TEST: update_user_profile ===")
        updated = service.update_user_profile(
            conn,
            user_id=u1["id"],
            first_name="UpdatedName",
            phone_number="999999999"
        )
        print("Updated:", updated)

        # ----- CHANGE ROLE (admin action) -----
        print("\n=== TEST: change_role ===")
        changed = service.change_role(
            conn,
            user_id=u2["id"],
            role_id=2
        )
        print("Role updated:", changed)

        # ----- DELETE (admin deletes someone else) -----
        print("\n=== TEST: delete user as ADMIN ===")
        deleted = service.delete(
            conn,
            target_user_id=u2["id"],
            current_user_id=u1["id"],
            current_user_role=u1["role_id"]
        )
        print("Deleted OK:", deleted)

        # ----- DELETE (customer tries to delete someone else → error) -----
        print("\n=== TEST: delete user as CUSTOMER (should fail) ===")
        try:
            service.delete(
                conn,
                target_user_id=u1["id"],
                current_user_id=999,       # random user
                current_user_role=3        # 3 = customer
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        # ----- DELETE (customer deletes himself → OK) -----
        print("\n=== TEST: delete self ===")
        u3 = service.create_user_admin(
            conn,
            email="test_user_3@example.com",
            password="secret123",
            first_name="Self",
            last_name="Delete",
            phone_number=None,
            role_id=3
        )
        try:
            result = service.delete(
                conn,
                target_user_id=u3["id"],   # mažu sám sebe
                current_user_id=u3["id"],
                current_user_role=u3["role_id"]
            )
            print("Self-delete OK:", result)
        except Exception as e:
            print("Unexpected error:", e)
