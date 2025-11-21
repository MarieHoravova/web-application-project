import sqlite3
from typing import Dict, Any, List, Optional


def create_contact_message(conn: sqlite3.Connection, name: str, email: str, message: str) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO contact_messages (name, email, message) VALUES (?, ?, ?)",
        (name.strip(), email.strip(), message.strip())
    )
    conn.commit()
    new_id = cur.lastrowid
    return get_contact_message_by_id(conn, new_id)


def get_contact_message_by_id(conn: sqlite3.Connection, msg_id: int) -> Optional[Dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM contact_messages WHERE id = ?",
        (msg_id,)
    ).fetchone()
    return dict(row) if row else None


def list_contact_messages(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM contact_messages ORDER BY created_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]
