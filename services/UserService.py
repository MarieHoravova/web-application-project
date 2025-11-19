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
    ROLE_ADMIN, ROLE_CUSTOMER, ROLE_RECEPTIONIST
)


class UserService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    # ADMIN, RECEPTIONIST: LIST USERS
    def list_users(self, current_user_role: int):
        if current_user_role == ROLE_ADMIN:
            return repo_list_users(self.conn)

        if current_user_role == ROLE_RECEPTIONIST:
            return repo_list_users_by_role(self.conn, ROLE_CUSTOMER)

        raise PermissionError("Nemáte oprávnění zobrazit uživatele")

    def list_users_by_role(self, role_id: int, current_user_role: int):
        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Pouze admin může filtrovat uživatele podle role")

        return repo_list_users_by_role(self.conn, role_id)

    # ADMIN: CREATE USER (např. sekretářka)
    def create_user_admin(
            self,
            email: str,
            password: str,
            first_name: str,
            last_name: str,
            phone_number: Optional[str],
            role_id: int,
            current_user_role: int
    ) -> Dict[str, any]:

        # --- Kontrola oprávnění ---
        if current_user_role == ROLE_RECEPTIONIST:
            # recepční smí vytvářet jen zákazníky
            if role_id != ROLE_CUSTOMER:
                raise PermissionError("Recepční může vytvářet pouze zákazníky")

        elif current_user_role != ROLE_ADMIN:
            # ostatní (customer) nesmí vytvářet vůbec
            raise PermissionError("Nemáte oprávnění vytvářet uživatele")

        # --- Validace unikátního emailu ---
        if repo_get_by_email(self.conn, email):
            raise ValueError("Uživatel s tímto emailem již existuje")

        # --- Hash hesla ---
        pwd_hash = hash_password(password)

        # --- Uložení uživatele ---
        return repo_create_user(
            self.conn,
            email=email,
            password_hash=pwd_hash,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role_id=role_id
        )

    # ADMIN: CHANGE USER ROLE
    def change_role(self, user_id: int, role_id: int):
        user = repo_get_by_id(self.conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        return repo_update_user(self.conn, user_id, role_id=role_id)

    # ADMIN / USER: UPDATE PROFILE
    # (admin pro jiné, user pro sebe)
    def update_user_profile(
        self,
        user_id: int,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None
    ):
        user = repo_get_by_id(self.conn, user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        return repo_update_user(
            self.conn,
            user_id=user_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )

    # ADMIN: DELETE USER
    # - Customer může mazat jen sám sebe
    # - Admin (ROLE_ADMIN) může mazat kohokoli
    def delete(self, target_user_id: int, current_user_id: int, current_user_role: int):
        user = repo_get_by_id(self.conn, target_user_id)
        if not user:
            raise ValueError("Uživatel neexistuje")

        # Pokud není admin, smí mazat jen sám sebe
        if current_user_role != ROLE_ADMIN and target_user_id != current_user_id:
            raise PermissionError("Nemáte oprávnění mazat tento účet")

        repo_delete_user(self.conn, target_user_id)
        return True


    # COMMON: GET USER
    def get_user_by_id(self, user_id: int) -> Dict[str, any] | None:
        return repo_get_by_id(self.conn, user_id)


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        service = UserService(conn)

        # ----- PREP: smažu staré testovací uživatele -----
        conn.execute("DELETE FROM users WHERE email LIKE 'test_user_%'")
        conn.commit()

        print("\n=== TEST: create_user_admin (ADMIN) ===")
        u1 = service.create_user_admin(
            email="test_user_1@example.com",
            password="secret123",
            first_name="Test",
            last_name="User1",
            phone_number="123456789",
            role_id=ROLE_ADMIN,
            current_user_role=ROLE_ADMIN
        )
        print("Created:", u1)

        print("\n=== TEST: create_user_admin (ADMIN vytváří CUSTOMER) ===")
        u2 = service.create_user_admin(
            email="test_user_2@example.com",
            password="secret123",
            first_name="Test",
            last_name="User2",
            phone_number=None,
            role_id=ROLE_CUSTOMER,
            current_user_role=ROLE_ADMIN
        )
        print("Created:", u2)

        print("\n=== TEST: create_user_admin (CUSTOMER -> FAIL) ===")
        try:
            service.create_user_admin(
                email="test_user_3@example.com",
                password="secret123",
                first_name="Self",
                last_name="Delete",
                phone_number=None,
                role_id=ROLE_CUSTOMER,
                current_user_role=ROLE_CUSTOMER
            )
        except PermissionError as e:
            print("Expected error:", e)

        print("\n=== TEST: list_users (ADMIN) ===")
        print(service.list_users(ROLE_ADMIN))

        print("\n=== TEST: list_users (RECEPTIONIST – only CUSTOMERS) ===")
        print(service.list_users(ROLE_RECEPTIONIST))

        print("\n=== TEST: list_users_by_role (ROLE_CUSTOMER) ===")
        print(service.list_users_by_role(ROLE_CUSTOMER, ROLE_ADMIN))

        print("\n=== TEST: list_users_by_role (FAIL – receptionist tries) ===")
        try:
            service.list_users_by_role(ROLE_CUSTOMER, ROLE_RECEPTIONIST)
        except PermissionError as e:
            print("Expected error:", e)

        print("\n=== TEST: get_user ===")
        print("Get u1:", service.get_user_by_id(u1["id"]))

        print("\n=== TEST: update_user_profile ===")
        updated = service.update_user_profile(
            user_id=u1["id"],
            first_name="UpdatedName",
            phone_number="999999999"
        )
        print("Updated:", updated)

        print("\n=== TEST: change_role ===")
        changed = service.change_role(
            user_id=u2["id"],
            role_id=ROLE_RECEPTIONIST
        )
        print("Role updated:", changed)

        print("\n=== TEST: delete user as ADMIN ===")
        deleted = service.delete(
            target_user_id=u2["id"],
            current_user_id=u1["id"],
            current_user_role=ROLE_ADMIN
        )
        print("Deleted OK:", deleted)

        print("\n=== TEST: delete user as CUSTOMER (should fail) ===")
        try:
            service.delete(
                target_user_id=u1["id"],
                current_user_id=999,
                current_user_role=ROLE_CUSTOMER
            )
        except PermissionError as e:
            print("Expected PermissionError:", e)

        print("\n=== TEST: delete self ===")
        u3 = service.create_user_admin(
            email="test_user_3@example.com",
            password="secret123",
            first_name="Self",
            last_name="Delete",
            phone_number=None,
            role_id=ROLE_CUSTOMER,
            current_user_role=ROLE_ADMIN
        )

        result = service.delete(
            target_user_id=u3["id"],
            current_user_id=u3["id"],
            current_user_role=ROLE_CUSTOMER
        )
        print("Self-delete OK:", result)
