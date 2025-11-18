import sqlite3
from typing import Optional, List, Dict, Any


def get_by_id(conn: sqlite3.Connection, user_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None

def get_by_email(conn: sqlite3.Connection, email: str) -> Optional[Dict[str, Any]]:
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None

def create_user(
    conn: sqlite3.Connection,
    email: str,
    password_hash: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str],
    role_id: int
) -> Dict[str, Any]:

    cur = conn.execute("""
        INSERT INTO users (email, password_hash, first_name, last_name, phone_number, role_id)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (email, password_hash, first_name, last_name, phone_number, role_id))

    conn.commit()
    user_id = cur.lastrowid
    return get_by_id(conn, user_id)

def update_user(
    conn: sqlite3.Connection,
    user_id: int,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    phone_number: Optional[str] = None,
    role_id: Optional[int] = None
) -> Optional[Dict[str, Any]]:
    updates = []
    params = []

    if email is not None:
        updates.append("email = ?")
        params.append(email.strip())

    if first_name is not None:
        updates.append("first_name = ?")
        params.append(first_name.strip())

    if last_name is not None:
        updates.append("last_name = ?")
        params.append(last_name.strip())

    if phone_number is not None:
        updates.append("phone_number = ?")
        params.append(phone_number.strip())

    if role_id is not None:
        updates.append("role_id = ?")
        params.append(role_id)

    if not updates:
        return get_by_id(conn, user_id)

    # MARK: user_id přidat až na konci, id až ve WHERE (pořadí argumentů)
    # ', '.join(updates) = spojení listu = "first_name = ?, phone_number = ?"
    params.append(user_id)
    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
    conn.execute(sql, params)
    conn.commit()

    return get_by_id(conn, user_id)


def delete_user(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()

def list_users(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM users ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]

def list_users_by_role(conn: sqlite3.Connection, role_id: int) -> List[Dict[str, Any]]:
    rows = conn.execute("SELECT * FROM users WHERE role_id = ?", (role_id,)).fetchall()
    return [dict(r) for r in rows]

def update_password(conn, user_id: int, hashed_password: str):
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_password, user_id))
    conn.commit()


# TEST
if __name__ == "__main__":
    from database.database import open_connection

    with open_connection() as conn:

        print("\n=== TEST: get_by_email (none yet) ===")
        print(get_by_email(conn, "test@example.com"))

        print("\n=== TEST: create_user ===")
        created = create_user(
            conn,
            email="test@example.com",
            password_hash="HASH123",
            first_name="John",
            last_name="Doe",
            phone_number="123456789",
            role_id=3
        )
        print(created)

        print("\n=== TEST: get_by_email ===")
        print(get_by_email(conn, "test@example.com"))

        print("\n=== TEST: update_user ===")
        updated = update_user(conn, created["id"], first_name="Johnny")
        print(updated)

        print("\n=== TEST: update_password ===")
        update_password(conn, created["id"], "NEW_HASH_999")
        print("Password after update:", get_by_id(conn, created["id"])["password_hash"])

        print("\n=== TEST: list_users ===")
        print(list_users(conn))

        print("\n=== TEST: delete_user ===")
        delete_user(conn, created["id"])

        print("\n=== TEST: get_by_id (should be None) ===")
        print(get_by_id(conn, created["id"]))

