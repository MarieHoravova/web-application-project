import sqlite3
from typing import List, Dict, Any, Optional

def get_reservation_item_by_id(conn: sqlite3.Connection, item_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM reservation_items WHERE id = ?", (item_id,)).fetchone()
    return dict(row) if row else None

# Reservation item = jedna rezervace pokoje, reservation = komplet rezervace
def list_reservation_items_by_reservation(conn: sqlite3.Connection, reservation_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservation_items WHERE reservation_id = ? ORDER BY check_in", (reservation_id,)).fetchall()
    return [dict(r) for r in rows]

def list_reservation_items_by_room(conn: sqlite3.Connection, room_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservation_items WHERE room_id = ? ORDER BY check_in", (room_id,)).fetchall()
    return [dict(r) for r in rows]

def create_reservation_item(conn: sqlite3.Connection, room_id: int, check_in: str, check_out: str, adults: int, children: int, reservation_id: int) -> Dict[str, Any]:
    cur = conn.execute("INSERT INTO reservation_items (room_id, check_in, check_out, adults, children, reservation_id) VALUES (?, ?, ?, ?, ?, ?)", (room_id, check_in, check_out, adults, children, reservation_id))
    conn.commit()
    new_id = cur.lastrowid
    return get_reservation_item_by_id(conn, new_id)

def delete_reservation_item(conn: sqlite3.Connection, item_id: int) -> None:
    conn.execute("DELETE FROM reservation_items WHERE id = ?", (item_id,))
    conn.commit()

# Tohle je kvůli rezervaci, aby si nemohl další člověk rezervovt pokoj ve stejném čase
def find_conflicting_reservation_items(conn: sqlite3.Connection, room_id: int, check_in: str, check_out: str) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservation_items WHERE room_id = ? AND NOT (check_out <= ? OR check_in >= ?)", (room_id, check_in, check_out)).fetchall()
    return [dict(r) for r in rows]
# Přehled příjezdů
def list_reservation_items_in_period(conn: sqlite3.Connection, date_from: str, date_to: str) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservation_items WHERE check_in >= ? AND check_in <= ? ORDER BY check_in", (date_from, date_to)).fetchall()
    return [dict(r) for r in rows]

if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== PREP: Ensure room exists ===")
        room = conn.execute("SELECT id FROM rooms LIMIT 1").fetchone()
        if room is None:
            cur = conn.execute("INSERT INTO rooms (number, room_type_id, room_status_id, image_path, floor) VALUES (?, ?, ?, ?, ?)", (999, 1, 1, "test.jpg", 1))
            conn.commit()
            room_id = cur.lastrowid
        else:
            room_id = room["id"]
        print("ROOM ID:", room_id)

        print("\n=== PREP: Ensure reservation (header) exists ===")
        reservation = conn.execute("SELECT id FROM reservations LIMIT 1").fetchone()
        if reservation is None:
            cur = conn.execute("INSERT INTO reservations (user_id, code, status_id) VALUES (?, ?, ?)", (1, "RES-TEST", 1))
            conn.commit()
            reservation_id = cur.lastrowid
        else:
            reservation_id = reservation["id"]
        print("RESERVATION ID:", reservation_id)

        conn.execute("DELETE FROM reservation_items WHERE reservation_id = ?", (reservation_id,))
        conn.commit()

        print("\n=== TEST: create_reservation_item ===")
        r1 = create_reservation_item(conn, room_id, "2025-01-10", "2025-01-15", 2, 0, reservation_id)
        print("Created:", r1)

        print("\n=== TEST: list_reservation_items_by_reservation ===")
        print(list_reservation_items_by_reservation(conn, reservation_id))

        print("\n=== TEST: list_reservation_items_by_room ===")
        print(list_reservation_items_by_room(conn, room_id))

        print("\n=== TEST: create 2nd reservation item (overlap) ===")
        r2 = create_reservation_item(conn, room_id, "2025-01-14", "2025-01-20", 2, 0, reservation_id)
        print("Created:", r2)

        print("\n=== TEST: find_conflicting_reservation_items (should find r1 and r2) ===")
        conflicts = find_conflicting_reservation_items(conn, room_id, "2025-01-12", "2025-01-18")
        print(conflicts)

        print("\n=== TEST: delete_reservation_item ===")
        delete_reservation_item(conn, r1["id"])
        delete_reservation_item(conn, r2["id"])
        print("After delete:", list_reservation_items_by_room(conn, room_id))


def find_conflicting_reservations():
    return None