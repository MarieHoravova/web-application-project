import sqlite3
from typing import List, Dict, Any, Optional

from repositories.PaymentMethodRepository import (
    get_by_id as repo_get_by_id,
    list_methods as repo_list_methods
)

class PaymentMethodService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def list_methods(self) -> List[Dict[str, Any]]:
        return repo_list_methods(self.conn)

    def get_method_by_id(self, method_id: int) -> Optional[Dict[str, Any]]:
        return repo_get_by_id(self.conn, method_id)

# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        service = PaymentMethodService(conn)

        print("\n=== TEST: list_methods ===")
        methods = service.list_methods()
        print("Methods:", methods)

        print("\n=== TEST: get_method_by_id (existing ID = 1) ===")
        m1 = service.get_method_by_id(1)
        print("Method 1:", m1)

        print("\n=== TEST: get_method_by_id (non-existing ID = 999) ===")
        m_none = service.get_method_by_id(999)
        print("Method 999:", m_none)
