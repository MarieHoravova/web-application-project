import sqlite3
from typing import List, Dict, Any, Optional


def get_room_type_by_id(conn: sqlite3.Connection, room_type_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM room_types WHERE id = ?", (room_type_id,)).fetchone()
    return dict(row) if row else None

def list_room_types(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM room_types ORDER BY id").fetchall()
    return [dict(r) for r in rows]

def create_room_type(conn: sqlite3.Connection, name: str, capacity: int, base_price: float, description: Optional[str] = None) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO room_types (name, capacity, base_price, description) VALUES (?, ?, ?, ?)",
        (name, capacity, base_price, description)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_room_type_by_id(conn, new_id)

def update_room_type(conn: sqlite3.Connection, room_type_id: int, name: Optional[str] = None, capacity: Optional[int] = None, base_price: Optional[float] = None, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name.strip())

    if capacity is not None:
        updates.append("capacity = ?")
        params.append(capacity)

    if base_price is not None:
        updates.append("base_price = ?")
        params.append(base_price)

    if description is not None:
        updates.append("description = ?")
        params.append(description.strip())

    if not updates:
        return get_room_type_by_id(conn, room_type_id)

    params.append(room_type_id)
    sql = f"UPDATE room_types SET {', '.join(updates)} WHERE id = ?"
    conn.execute(sql, params)
    conn.commit()

    return get_room_type_by_id(conn, room_type_id)

def delete_room_type(conn: sqlite3.Connection, room_type_id: int) -> None:
    conn.execute("DELETE FROM room_types WHERE id = ?", (room_type_id,))
    conn.commit()

# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== TEST: get_room_type_by_id ===")
        print(get_room_type_by_id(conn, 1))

        print("\n=== TEST: list_room_types ===")
        print(list_room_types(conn))

        print("\n=== TEST: create_room_type ===")
        rt = create_room_type(conn, "Test type", 2, 1000.0, "Test description")
        print(rt)

        print("\n=== TEST: update_room_type ===")
        updated = update_room_type(conn, rt["id"], base_price=1200.0)
        print(updated)

        print("\n=== TEST: delete_room_type ===")
        delete_room_type(conn, rt["id"])
        print(get_room_type_by_id(conn, rt["id"]))
