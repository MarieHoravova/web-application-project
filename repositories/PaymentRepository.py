import sqlite3
from typing import List, Dict, Any, Optional


def get_payment_by_id(conn: sqlite3.Connection, payment_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
    return dict(row) if row else None

def list_all_payments(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM payments ORDER BY paid_at DESC").fetchall()
    return [dict(r) for r in rows]

def list_payments_by_reservation(conn: sqlite3.Connection, reservation_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM payments WHERE reservation_id = ? ORDER BY paid_at", (reservation_id,)).fetchall()
    return [dict(r) for r in rows]

def create_payment(conn: sqlite3.Connection, reservation_id: int, amount: float, method_id: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO payments (reservation_id, amount, method_id) VALUES (?, ?, ?)",
        (reservation_id, amount, method_id)
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
        print("\n=== PREP: ensure reservation exists ===")
        reservation = conn.execute("SELECT id FROM reservations LIMIT 1").fetchone()
        if reservation is None:
            cur = conn.execute(
                "INSERT INTO reservations (user_id, code, status_id, created_at) VALUES (1, 'PAYTEST', 1, datetime('now'))"
            )
            conn.commit()
            reservation_id = cur.lastrowid
        else:
            reservation_id = reservation["id"]

        print("Using reservation ID:", reservation_id)

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
        payment = create_payment(conn, reservation_id=reservation_id, amount=1500.0, method_id=method_id)
        print("Created:", payment)

        print("\n=== TEST: list_all_payments ===")
        print(list_all_payments(conn))

        print("\n=== TEST: list_payments_by_reservation ===")
        print(list_payments_by_reservation(conn, reservation_id))

        print("\n=== TEST: delete_payment ===")
        delete_payment(conn, payment["id"])
        print("After delete:", get_payment_by_id(conn, payment["id"]))