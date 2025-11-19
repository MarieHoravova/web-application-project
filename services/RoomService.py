import sqlite3
from typing import List, Dict, Any, Optional

from repositories.RoomRepository import (
    get_room_by_id as repo_get_by_id,
    list_rooms as repo_list_rooms,
    list_rooms_by_status as repo_list_by_status,
    list_rooms_by_type as repo_list_by_type,
    create_room as repo_create_room,
    update_room as repo_update_room,
    delete_room as repo_delete_room,
)

from domain.constants import ROLE_ADMIN, ROLE_RECEPTIONIST, ROLE_CUSTOMER


class RoomService:

    # ---- GET ----
    def get_room(self, conn: sqlite3.Connection, room_id: int):
        return repo_get_by_id(conn, room_id)

    # ---- LIST ----
    def list_rooms(self, conn: sqlite3.Connection):
        return repo_list_rooms(conn)

    def list_rooms_by_status(self, conn: sqlite3.Connection, status_id: int):
        return repo_list_by_status(conn, status_id)

    def list_rooms_by_type(self, conn: sqlite3.Connection, room_type_id: int):
        return repo_list_by_type(conn, room_type_id)

    # ---- CREATE (ADMIN ONLY) ----
    def create_room(
        self,
        conn: sqlite3.Connection,
        number: int,
        room_type_id: int,
        room_status_id: int,
        image_path: str,
        floor: int,
        current_user_role: int
    ) -> Dict[str, Any]:

        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Pouze admin může vytvářet pokoje")

        return repo_create_room(
            conn,
            number,
            room_type_id,
            room_status_id,
            image_path,
            floor
        )

    # ---- UPDATE (ADMIN or RECEPCE) ----
    def update_room(
        self,
        conn: sqlite3.Connection,
        room_id: int,
        current_user_role: int,
        number: Optional[int] = None,
        room_type_id: Optional[int] = None,
        room_status_id: Optional[int] = None,
        image_path: Optional[str] = None,
        floor: Optional[int] = None
    ) -> Dict[str, Any]:

        if current_user_role not in (ROLE_ADMIN, ROLE_RECEPTIONIST):
            raise PermissionError("Nemáte oprávnění upravovat pokoje")

        room = repo_get_by_id(conn, room_id)
        if not room:
            raise ValueError("Pokoj neexistuje")

        updated = repo_update_room(
            conn,
            room_id,
            number,
            room_type_id,
            room_status_id,
            image_path,
            floor
        )
        return updated

    # ---- DELETE (ADMIN ONLY) ----
    def delete_room(self, conn: sqlite3.Connection, room_id: int, current_user_role: int):

        if current_user_role != ROLE_ADMIN:
            raise PermissionError("Pouze admin může mazat pokoje")

        room = repo_get_by_id(conn, room_id)
        if not room:
            raise ValueError("Pokoj neexistuje")

        repo_delete_room(conn, room_id)
        return True


# TEST
if __name__ == "__main__":
    from database.database import open_connection
    service = RoomService()

    with open_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        print("\n=== PREP: clean test rooms ===")
        conn.execute("DELETE FROM rooms WHERE number >= 900")
        conn.commit()

        # --- CREATE admin + receptionist ---
        admin_id = conn.execute(
            "INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)"
            " VALUES ('room_admin@example.com', 'X', 'R', 'A', 1, datetime('now'))"
        ).lastrowid

        rec_id = conn.execute(
            "INSERT INTO users (email, password_hash, first_name, last_name, role_id, created_at)"
            " VALUES ('room_rec@example.com', 'X', 'R', 'R', 2, datetime('now'))"
        ).lastrowid

        conn.commit()

        print("\n=== TEST: create_room (admin OK) ===")
        room = service.create_room(
            conn,
            number=900,
            room_type_id=1,
            room_status_id=1,
            image_path="img.jpg",
            floor=9,
            current_user_role=ROLE_ADMIN
        )
        print("Created:", room)
        room_id = room["id"]

        print("\n=== TEST: create_room as receptionist (FAIL) ===")
        try:
            service.create_room(
                conn,
                number=901,
                room_type_id=1,
                room_status_id=1,
                image_path="img.jpg",
                floor=9,
                current_user_role=ROLE_RECEPTIONIST
            )
        except PermissionError as e:
            print("Expected:", e)

        print("\n=== TEST: update_room as receptionist (OK) ===")
        updated = service.update_room(
            conn,
            room_id,
            current_user_role=ROLE_RECEPTIONIST,
            floor=10
        )
        print("Updated:", updated)

        print("\n=== TEST: update_room as customer (FAIL) ===")
        try:
            service.update_room(
                conn,
                room_id,
                current_user_role=ROLE_CUSTOMER,
                floor=11
            )
        except PermissionError as e:
            print("Expected:", e)

        print("\n=== TEST: delete_room as admin (OK) ===")
        result = service.delete_room(conn, room_id, ROLE_ADMIN)
        print("Deleted:", result)

        print("\n=== TEST: delete_room as receptionist (FAIL) ===")
        try:
            service.delete_room(conn, room_id, ROLE_RECEPTIONIST)
        except PermissionError as e:
            print("Expected:", e)
