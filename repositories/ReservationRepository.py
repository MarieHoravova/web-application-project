import sqlite3
from typing import List, Dict, Any, Optional


def get_reservation_by_id(conn: sqlite3.Connection, reservation_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    return dict(row) if row else None

def get_reservation_by_code(conn: sqlite3.Connection, code: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM reservations WHERE code = ?", (code,)).fetchone()
    return dict(row) if row else None

def list_reservations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservations ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]

def list_reservations_by_user(conn: sqlite3.Connection, user_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM reservations WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [dict(r) for r in rows]

def create_reservation(conn: sqlite3.Connection, user_id: int, code: str, status_id: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO reservations (user_id, code, status_id) VALUES (?, ?, ?)",
        (user_id, code, status_id)
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_reservation_by_id(conn, new_id)

def update_reservation_status(conn: sqlite3.Connection, reservation_id: int, status_id: int) -> Optional[Dict[str, Any]]:
    conn.execute("UPDATE reservations SET status_id = ? WHERE id = ?", (status_id, reservation_id))
    conn.commit()
    return get_reservation_by_id(conn, reservation_id)

# Speciální update reservation pro admina – řeší výjimečné
# případy (např. chybně přiřazený uživatel nebo kód)
def update_reservation(
    conn: sqlite3.Connection,
    reservation_id: int,
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
        return get_reservation_by_id(conn, reservation_id)

    params.append(reservation_id)
    sql = f"UPDATE reservations SET {', '.join(updates)} WHERE id = ?"

    conn.execute(sql, params)
    conn.commit()

    return get_reservation_by_id(conn, reservation_id)

def delete_reservation(conn: sqlite3.Connection, reservation_id: int) -> None:
    conn.execute("DELETE FROM reservations WHERE id = ?", (reservation_id,))
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
                ("reservation_test@example.com", "HASH123", "Reservation", "Tester", "123456789", 3)
            )
            conn.commit()
            user_id = cur.lastrowid
        else:
            user_id = user_row["id"]

        # 2) Reservation status
        status_row = conn.execute("SELECT id FROM reservation_statuses ORDER BY id LIMIT 1").fetchone()
        if status_row is None:
            cur = conn.execute("INSERT INTO reservation_statuses (description) VALUES (?)", ("pending",))
            conn.commit()
            status_id = cur.lastrowid
        else:
            status_id = status_row["id"]

        # 3) Úklid testovacích reservation kódů, abych ho mohla pouštět opakovaně
        conn.execute("DELETE FROM reservations WHERE code = ?", ("TEST-CODE-123",))
        conn.execute("DELETE FROM reservations WHERE code = ?", ("ABC123",))
        conn.execute("DELETE FROM reservations WHERE code = ?", ("NEW999",))
        conn.commit()

        print("\n=== TEST: list_reservations (before) ===")
        print(list_reservations(conn))

        print("\n=== TEST: create_reservation ===")
        reservation = create_reservation(conn, user_id=user_id, code="TEST-CODE-123", status_id=status_id)
        print("Created:", reservation)

        reservation_id = reservation["id"]

        print("\n=== TEST: get_reservation_by_id ===")
        print(get_reservation_by_id(conn, reservation_id))

        print("\n=== TEST: get_reservation_by_code ===")
        print(get_reservation_by_code(conn, "TEST-CODE-123"))

        print("\n=== TEST: list_reservations_by_user ===")
        print(list_reservations_by_user(conn, user_id=user_id))

        print("\n=== TEST: update_reservation_status ===")
        updated = update_reservation_status(conn, reservation_id, status_id=status_id)
        print("Updated:", updated)

        print("\n=== TEST: update_reservation (admin-only operation) ===")
        bk = create_reservation(conn, user_id=user_id, code="ABC123", status_id=status_id)
        updated_reservation = update_reservation(conn, bk["id"], user_id=user_id, code="NEW999")
        print(updated_reservation)

        print("\n=== TEST: delete_reservation ===")
        delete_reservation(conn, reservation_id)
        print("After delete get_by_id:", get_reservation_by_id(conn, reservation_id))

        print("\n=== TEST: list_reservations (after) ===")
        print(list_reservations(conn))
