import sqlite3
from typing import List, Dict, Any, Optional

from repositories.PaymentMethodRepository import (
    get_by_id as repo_get_by_id,
    list_methods as repo_list_methods
)

class PaymentMethodService:
    def list_methods(self, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        return repo_list_methods(conn)

    def get_method_by_id(self, conn: sqlite3.Connection, method_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(conn, method_id)

# TEST
if __name__ == "__main__":
    from database.database import open_connection

    service = PaymentMethodService()

    with open_connection() as conn:
        print("\n=== TEST: list_methods ===")
        methods = service.list_methods(conn)
        print("Methods:", methods)

        print("\n=== TEST: get_method_by_id (existing ID = 1) ===")
        m1 = service.get_method_by_id(conn, 1)
        print("Method 1:", m1)

        print("\n=== TEST: get_method_by_id (non-existing ID = 999) ===")
        m_none = service.get_method_by_id(conn, 999)
        print("Method 999:", m_none)
