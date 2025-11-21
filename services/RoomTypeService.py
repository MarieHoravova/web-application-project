import sqlite3
from typing import List, Dict, Any, Optional

from repositories.RoomTypeRepository import (
    get_room_type_by_id as repo_get_by_id,
    list_room_types as repo_list_room_types,
    create_room_type as repo_create,
    update_room_type as repo_update,
    delete_room_type as repo_delete
)

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


class RoomTypeService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def get_room_type_by_id(self, room_type_id: int):
        return repo_get_by_id(self.conn, room_type_id)

    def list_room_types(self):
        return repo_list_room_types(self.conn)

    # ---- CREATE ----
    def create_room_type(
        self,
        name: str,
        capacity: int,
        base_price: float,
        description: Optional[str],
        current_user_role: int
    ):
        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Pouze admin může vytvářet typy pokojů")

        return repo_create(self.conn, name, capacity, base_price, description)

    # ---- UPDATE ----
    def update_room_type(
        self,
        room_type_id: int,
        current_user_role: int,
        name: Optional[str] = None,
        capacity: Optional[int] = None,
        base_price: Optional[float] = None,
        description: Optional[str] = None
    ):
        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění upravovat typ pokoje")

        room_type = repo_get_by_id(self.conn, room_type_id)
        if not room_type:
            raise ValueError("Typ pokoje neexistuje")

        return repo_update(self.conn, room_type_id, name, capacity, base_price, description)

    # ---- DELETE ----
    def delete_room_type(
        self,
        room_type_id: int,
        current_user_role: int
    ):
        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Pouze admin může mazat typy pokojů")

        room_type = repo_get_by_id(self.conn, room_type_id)
        if not room_type:
            raise ValueError("Typ pokoje neexistuje")

        repo_delete(self.conn, room_type_id)
        return True


if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        service = RoomTypeService(conn)

        print("\n=== PREP: clean old room types ===")
        conn.execute("DELETE FROM room_types WHERE name LIKE 'TestType%'")
        conn.commit()

        admin_role = ROLE_ADMIN
        rec_role = ROLE_RECEPTIONIST
        cust_role = ROLE_CUSTOMER

        print("\n=== TEST: create_room_type (admin OK) ===")
        rt = service.create_room_type("TestType1", 2, 1200.0, "desc", admin_role)
        print("Created:", rt)
        rt_id = rt["id"]

        print("\n=== TEST: create_room_type (receptionist FAIL) ===")
        try:
            service.create_room_type("TestType2", 3, 1500.0, None, rec_role)
        except PermissionError as e:
            print("Expected:", e)

        print("\n=== TEST: update_room_type (receptionist OK) ===")
        updated = service.update_room_type(rt_id, rec_role, base_price=1300.0)
        print("Updated:", updated)

        print("\n=== TEST: update_room_type (customer FAIL) ===")
        try:
            service.update_room_type(rt_id, cust_role, base_price=1500.0)
        except PermissionError as e:
            print("Expected:", e)

        print("\n=== TEST: delete_room_type (admin OK) ===")
        deleted = service.delete_room_type(rt_id, admin_role)
        print("Deleted:", deleted)

        print("\n=== TEST: delete_room_type (receptionist FAIL) ===")
        try:
            service.delete_room_type(rt_id, rec_role)
        except PermissionError as e:
            print("Expected:", e)
