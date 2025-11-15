import sqlite3
from typing import List, Dict, Any, Optional


def get_booking_by_id(conn: sqlite3.Connection, booking_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(row) if row else None

def get_booking_by_code(conn: sqlite3.Connection, code: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM bookings WHERE code = ?", (code,)).fetchone()
    return dict(row) if row else None

def list_bookings(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM bookings ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def list_bookings_by_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM bookings WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]

def create_booking(conn: sqlite3.Connection, user_id: int, code: str, status_id: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO bookings (user_id, code, status_id) VALUES (?, ?, ?)",
        (user_id, code, status_id)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_booking_by_id(conn, new_id)

def update_booking_status(conn: sqlite3.Connection, booking_id: int, status_id: int) -> Optional[Dict[str, Any]]:
    conn.execute("UPDATE bookings SET status_id = ? WHERE id = ?", (status_id, booking_id))
    conn.commit()
    return get_booking_by_id(conn, booking_id)

# Speciální update bookingu pro admina – řeší výjimečné
# případy (např. chybně přiřazený uživatel nebo kód)
def update_booking(
    conn: sqlite3.Connection,
    booking_id: int,
    user_id: Optional[int] = None,
    code: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    updates = []
    params = []

    if user_id is not None:
        updates.append("user_id = ?")
        params.append(user_id)

    if code is not None:
        updates.append("code = ?")
        params.append(code.strip())

    if not updates:
        return get_booking_by_id(conn, booking_id)

    params.append(booking_id)
    sql = f"UPDATE bookings SET {', '.join(updates)} WHERE id = ?"

    conn.execute(sql, params)
    conn.commit()

    return get_booking_by_id(conn, booking_id)

def delete_booking(conn: sqlite3.Connection, booking_id: int) -> None:
    conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    conn.commit()


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON")

        # 1) Testovací user
        user_row = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
        if user_row is None:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id, created_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
                ("booking_test@example.com", "HASH123", "Booking", "Tester", "123456789", 3)
            )
            conn.commit()
            user_id = cur.lastrowid
        else:
            user_id = user_row["id"]

        # 2) Booking status
        status_row = conn.execute("SELECT id FROM booking_statuses ORDER BY id LIMIT 1").fetchone()
        if status_row is None:
            cur = conn.execute("INSERT INTO booking_statuses (description) VALUES (?)", ("pending",))
            conn.commit()
            status_id = cur.lastrowid
        else:
            status_id = status_row["id"]

        # 3) Úklid testovacích booking kódů, abych ho mohla pouštět opakovaně
        conn.execute("DELETE FROM bookings WHERE code = ?", ("TEST-CODE-123",))
        conn.execute("DELETE FROM bookings WHERE code = ?", ("ABC123",))
        conn.execute("DELETE FROM bookings WHERE code = ?", ("NEW999",))
        conn.commit()

        print("\n=== TEST: list_bookings (before) ===")
        print(list_bookings(conn))

        print("\n=== TEST: create_booking ===")
        booking = create_booking(conn, user_id=user_id, code="TEST-CODE-123", status_id=status_id)
        print("Created:", booking)

        booking_id = booking["id"]

        print("\n=== TEST: get_booking_by_id ===")
        print(get_booking_by_id(conn, booking_id))

        print("\n=== TEST: get_booking_by_code ===")
        print(get_booking_by_code(conn, "TEST-CODE-123"))

        print("\n=== TEST: list_bookings_by_user ===")
        print(list_bookings_by_user(conn, user_id=user_id))

        print("\n=== TEST: update_booking_status ===")
        updated = update_booking_status(conn, booking_id, status_id=status_id)
        print("Updated:", updated)

        print("\n=== TEST: update_booking (admin-only operation) ===")
        bk = create_booking(conn, user_id=user_id, code="ABC123", status_id=status_id)
        updated_booking = update_booking(conn, bk["id"], user_id=user_id, code="NEW999")
        print(updated_booking)

        print("\n=== TEST: delete_booking ===")
        delete_booking(conn, booking_id)
        print("After delete get_by_id:", get_booking_by_id(conn, booking_id))

        print("\n=== TEST: list_bookings (after) ===")
        print(list_bookings(conn))
