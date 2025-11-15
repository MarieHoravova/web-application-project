import sqlite3

def get_by_id(conn: sqlite3.Connection, status_id: int):
    row = conn.execute(
        "SELECT * FROM room_statuses WHERE id = ?", (status_id,)
    ).fetchone()
    return dict(row) if row else None


def list_room_statuses(conn: sqlite3.Connection):
    rows = conn.execute("SELECT * FROM room_statuses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== TEST: list_room_statuses ===")
        print(list_room_statuses(conn))

        print("\n=== TEST: get_by_id ===")
        print(get_by_id(conn, 1))
