import sqlite3
from typing import List, Dict, Any, Optional


def get_reservation_by_id(conn: sqlite3.Connection, reservation_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    return dict(row) if row else None

def list_reservations_by_booking(conn: sqlite3.Connection, booking_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservations WHERE booking_id = ? ORDER BY check_in", (booking_id,)).fetchall()
    return [dict(r) for r in rows]

def list_reservations_by_room(conn: sqlite3.Connection, room_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservations WHERE room_id = ? ORDER BY check_in", (room_id,)).fetchall()
    return [dict(r) for r in rows]

def create_reservation(conn: sqlite3.Connection, room_id: int, check_in: str, check_out: str, adults: int, children: int, booking_id: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO reservations (room_id, check_in, check_out, adults, children, booking_id) VALUES (?, ?, ?, ?, ?, ?)",
        (room_id, check_in, check_out, adults, children, booking_id)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_reservation_by_id(conn, new_id)

def delete_reservation(conn: sqlite3.Connection, reservation_id: int) -> None:
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
    conn.commit()

def find_conflicting_reservations(conn: sqlite3.Connection, room_id: int, check_in: str, check_out: str) -> List[Dict[str, Any]]:
    """
    Najde rezervace, které kolidují s intervalem [check_in, check_out) pro daný pokoj.
    Logika:
        konflikt existuje, pokud NEnastane:
        (existující_checkout <= nový_checkin) OR (existující_checkin >= nový_checkout)
        -> proto NOT (A OR B)
    """
    rows = conn.execute(
        """
        SELECT * FROM reservations
        WHERE room_id = ?
        AND NOT (check_out <= ? OR check_in >= ?)
        """,
        (room_id, check_in, check_out)
    ).fetchall()
    return [dict(r) for r in rows]


if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:

        print("\n=== PREP: Ensure room exists ===")
        room = conn.execute("SELECT id FROM rooms LIMIT 1").fetchone()
        if room is None:
            cur = conn.execute(
                "INSERT INTO rooms (number, room_type_id, room_status_id, image_path, floor) VALUES (?, ?, ?, ?, ?)",
                (999, 1, 1, "test.jpg", 1)
            )
            conn.commit()
            room_id = cur.lastrowid
        else:
            room_id = room["id"]
        print("ROOM ID:", room_id)

        print("\n=== PREP: Ensure booking exists ===")
        booking = conn.execute("SELECT id FROM bookings LIMIT 1").fetchone()
        if booking is None:
            cur = conn.execute(
                "INSERT INTO bookings (user_id, code, status_id) VALUES (?, ?, ?)",
                (1, "RES-TEST", 1)
            )
            conn.commit()
            booking_id = cur.lastrowid
        else:
            booking_id = booking["id"]
        print("BOOKING ID:", booking_id)

        # Clean old test reservations
        conn.execute("DELETE FROM reservations WHERE booking_id = ?", (booking_id,))
        conn.commit()

        print("\n=== TEST: create_reservation ===")
        r1 = create_reservation(conn, room_id, "2025-01-10", "2025-01-15", 2, 0, booking_id)
        print("Created:", r1)

        print("\n=== TEST: list_reservations_by_booking ===")
        print(list_reservations_by_booking(conn, booking_id))

        print("\n=== TEST: list_reservations_by_room ===")
        print(list_reservations_by_room(conn, room_id))

        print("\n=== TEST: create 2nd reservation (overlap) ===")
        r2 = create_reservation(conn, room_id, "2025-01-14", "2025-01-20", 2, 0, booking_id)
        print("Created:", r2)

        print("\n=== TEST: find_conflicting_reservations (should find r1) ===")
        conflicts = find_conflicting_reservations(conn, room_id, "2025-01-12", "2025-01-18")
        print(conflicts)

        print("\n=== TEST: delete_reservation ===")
        delete_reservation(conn, r1["id"])
        delete_reservation(conn, r2["id"])
        print("After delete:", list_reservations_by_room(conn, room_id))
