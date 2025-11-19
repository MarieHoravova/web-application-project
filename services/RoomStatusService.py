import sqlite3
from typing import List, Dict, Any, Optional

from repositories.RoomStatusRepository import (
    get_by_id as repo_get_by_id,
    list_room_statuses as repo_list_statuses
)

class RoomStatusService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_statuses(self) -> List[Dict[str, Any]]:
        return repo_list_statuses(self.conn)

    def get_room_status_by_id(self, status_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(self.conn, status_id)


if __name__ == "__main__":
    from database.database import open_connection


    with open_connection() as conn:
        service = RoomStatusService(conn)

        print("\n=== TEST: list_statuses ===")
        statuses = service.list_statuses()
        print("Statuses:", statuses)

        print("\n=== TEST: get_by_id (existing ID = 1) ===")
        st1 = service.get_room_status_by_id(1)
        print("Status 1:", st1)

        print("\n=== TEST: get_by_id (non-existing ID = 999) ===")
        st_none = service.get_room_status_by_id(999)
        print("Status 999:", st_none)
