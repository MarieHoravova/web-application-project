import sqlite3

def get_by_id(conn: sqlite3.Connection, method_id: int):
    row = conn.execute(
        "SELECT * FROM payment_methods WHERE id = ?", (method_id,)
    ).fetchone()
    return dict(row) if row else None


def list_methods(conn: sqlite3.Connection):
    rows = conn.execute("SELECT * FROM payment_methods ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== TEST: list_methods ===")
        print(list_methods(conn))

        print("\n=== TEST: get_by_id ===")
        print(get_by_id(conn, 1))
