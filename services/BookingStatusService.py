import sqlite3
from typing import List, Dict, Any, Optional

from repositories.BookingStatusRepository import (
    get_by_id as repo_get_by_id,
    list_statuses as repo_list_statuses
)

class BookingStatusService:
    def list_statuses(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        return repo_list_statuses(conn)

    def get_by_id(self, conn: sqlite3.Connection, status_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(conn, status_id)

if __name__ == "__main__":
    from database.database import open_connection

    service = BookingStatusService()

    with open_connection() as conn:
        print("\n=== TEST: list_statuses ===")
        statuses = service.list_statuses(conn)
        print("Statuses:", statuses)

        print("\n=== TEST: get_by_id (existing ID = 1) ===")
        status1 = service.get_by_id(conn, 1)
        print("Status 1:", status1)

        print("\n=== TEST: get_by_id (non-existing ID = 999) ===")
        status_none = service.get_by_id(conn, 999)
        print("Status 999:", status_none)



