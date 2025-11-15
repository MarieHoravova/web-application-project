import sqlite3

def get_by_id(conn: sqlite3.Connection, role_id: int):
    row = conn.execute(
        "SELECT * FROM roles WHERE id = ?", (role_id,)
    ).fetchone()
    return dict(row) if row else None

def list_roles(conn: sqlite3.Connection):
    rows = conn.execute("SELECT * FROM roles ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== TEST: list_roles ===")
        print(list_roles(conn))

        print("\n=== TEST: get_by_id ===")
        print(get_by_id(conn, 1))
