import sqlite3
from typing import List, Dict, Any, Optional


def get_room_by_id(conn: sqlite3.Connection, room_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    return dict(row) if row else None

def list_rooms(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM rooms ORDER BY floor, number").fetchall()
    return [dict(r) for r in rows]

def list_rooms_by_status(conn: sqlite3.Connection, status_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM rooms WHERE room_status_id = ? ORDER BY floor, number", (status_id,)).fetchall()
    return [dict(r) for r in rows]

def list_rooms_by_type(conn: sqlite3.Connection, room_type_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM rooms WHERE room_type_id = ? ORDER BY floor, number", (room_type_id,)).fetchall()
    return [dict(r) for r in rows]

def create_room(conn: sqlite3.Connection, number: int, room_type_id: int, room_status_id: int, image_path: str, floor: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO rooms (number, room_type_id, room_status_id, image_path, floor) VALUES (?, ?, ?, ?, ?)",
        (number, room_type_id, room_status_id, image_path, floor)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_room_by_id(conn, new_id)

def update_room(conn: sqlite3.Connection, room_id: int, number: Optional[int] = None, room_type_id: Optional[int] = None, room_status_id: Optional[int] = None, image_path: Optional[str] = None, floor: Optional[int] = None) -> Optional[Dict[str, Any]]:
    updates = []
    params = []

    if number is not None:
        updates.append("number = ?")
        params.append(number)

    if room_type_id is not None:
        updates.append("room_type_id = ?")
        params.append(room_type_id)

    if room_status_id is not None:
        updates.append("room_status_id = ?")
        params.append(room_status_id)

    if image_path is not None:
        updates.append("image_path = ?")
        params.append(image_path.strip())

    if floor is not None:
        updates.append("floor = ?")
        params.append(floor)

    if not updates:
        return get_room_by_id(conn, room_id)

    params.append(room_id)
    sql = f"UPDATE rooms SET {', '.join(updates)} WHERE id = ?"
    conn.execute(sql, params)
    conn.commit()

    return get_room_by_id(conn, room_id)

def delete_room(conn: sqlite3.Connection, room_id: int) -> None:
    conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
    conn.commit()

# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== TEST: list_rooms (before) ===")
        print(list_rooms(conn))

        print("\n=== TEST: create_room ===")
        # POZOR: tady musí existovat room_type_id=1 a room_status_id=1 v DB!
        new_room = create_room(
            conn,
            number=999,
            room_type_id=1,
            room_status_id=1,
            image_path="test.jpg",
            floor=9
        )
        print("Created:", new_room)

        new_id = new_room["id"]

        print("\n=== TEST: get_room_by_id ===")
        print(get_room_by_id(conn, new_id))

        print("\n=== TEST: list_rooms_by_type ===")
        print(list_rooms_by_type(conn, room_type_id=1))

        print("\n=== TEST: list_rooms_by_status ===")
        print(list_rooms_by_status(conn, status_id=1))

        print("\n=== TEST: update_room (change status + floor) ===")
        updated = update_room(conn, new_id, room_status_id=2, floor=10)
        print("Updated:", updated)

        print("\n=== TEST: delete_room ===")
        delete_room(conn, new_id)
        print("After delete get_by_id:", get_room_by_id(conn, new_id))

        print("\n=== TEST: list_rooms (after) ===")
        print(list_rooms(conn))
