import sqlite3
from typing import Optional, Dict, Any
from repositories.RoleRepository import (
    get_by_id as repo_get_by_id,
    list_roles as repo_list_roles
,)

class RoleService:
    def get_role_by_id(self, conn: sqlite3.Connection, role_id: int):
        return repo_get_by_id(conn, role_id)

    def list_roles(self, conn: sqlite3.Connection):
        return repo_list_roles(conn)


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    service = RoleService()

    with open_connection() as conn:

        print("\n=== TEST: list_roles ===")
        roles = service.list_roles(conn)
        print("Roles:", roles)

        print("\n=== TEST: get_role_by_id (existing ID = 1) ===")
        role1 = service.get_role_by_id(conn, 1)
        print("Role 1:", role1)

        print("\n=== TEST: get_role_by_id (non-existing ID = 999) ===")
        role_none = service.get_role_by_id(conn, 999)
        print("Role 999:", role_none)

