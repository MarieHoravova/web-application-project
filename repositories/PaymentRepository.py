import sqlite3
from typing import List, Dict, Any, Optional


def get_payment_by_id(conn: sqlite3.Connection, payment_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None

def list_all_payments(conn: sqlite3.Connection):
    rows = conn.execute("SELECT * FROM payments ORDER BY paid_at DESC").fetchall()
    return [dict(r) for r in rows]

def list_payments_by_booking(conn: sqlite3.Connection, booking_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM payments WHERE booking_id = ? ORDER BY paid_at", (booking_id,)).fetchall()
    return [dict(r) for r in rows]

def create_payment(conn: sqlite3.Connection, booking_id: int, amount: float, method_id: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO payments (booking_id, amount, method_id) VALUES (?, ?, ?)",
        (booking_id, amount, method_id)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_payment_by_id(conn, new_id)

def delete_payment(conn: sqlite3.Connection, payment_id: int) -> None:
    conn.execute("DELETE FROM payments WHERE id = ?", (payment_id,))
    conn.commit()


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:
        print("\n=== PREP: ensure booking exists ===")
        booking = conn.execute("SELECT id FROM bookings LIMIT 1").fetchone()
        if booking is None:
            cur = conn.execute(
                "INSERT INTO bookings (user_id, code, status_id, created_at) VALUES (1, 'PAYTEST', 1, datetime('now'))"
            )
            conn.commit()
            booking_id = cur.lastrowid
        else:
            booking_id = booking["id"]

        print("Using booking ID:", booking_id)

        print("\n=== PREP: ensure payment method exists ===")
        method = conn.execute("SELECT id FROM payment_methods LIMIT 1").fetchone()
        if method is None:
            cur = conn.execute("INSERT INTO payment_methods (description) VALUES ('cash')")
            conn.commit()
            method_id = cur.lastrowid
        else:
            method_id = method["id"]

        print("Using method ID:", method_id)

        print("\n=== TEST: create_payment ===")
        payment = create_payment(conn, booking_id=booking_id, amount=1500.0, method_id=method_id)
        print("Created:", payment)

        print("\n=== TEST: list_all_payments ===")
        print(list_all_payments(conn))

        print("\n=== TEST: list_payments_by_booking ===")
        print(list_payments_by_booking(conn, booking_id))

        print("\n=== TEST: delete_payment ===")
        delete_payment(conn, payment["id"])
        print("After delete:", get_payment_by_id(conn, payment["id"]))