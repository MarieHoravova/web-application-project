import sqlite3
from typing import List, Dict, Any, Optional
from domain.constants import ROOM_STATUS_AVAILABLE, ROOM_TYPE_STANDART

import sqlite3
from typing import List, Dict, Any, Optional


# from domain.constants import ROOM_STATUS_AVAILABLE, ROOM_TYPE_STANDART # (pokud používáš)

def _map_room_full(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Mapuje řádek z DB na objekt Room s vnořenými objekty room_type a room_status.
    """
    if not row:
        return None

    item = dict(row)

    # Základní image_path vezmeme z typu pokoje, pokud je k dispozici
    if "type_image_path" in item and item["type_image_path"]:
        item["image_path"] = item["type_image_path"]

    # 1. Mapování Room Type
    if 'type_name' in item and item['type_name']:
        item['room_type'] = {
            'id': item['room_type_id'],
            'name': item['type_name'],
            'base_price': item.get('base_price'),
            'capacity': item.get('capacity'),
            'description': item.get('type_desc'),
            'image_path': item.get('type_image_path'),
        }
    else:
        item['room_type'] = None

    # 2. Mapování Room Status
    if 'status_desc' in item and item['status_desc']:
        item['room_status'] = {
            'id': item['room_status_id'],
            'description': item['status_desc']  # Např. "available", "dirty"
        }
    else:
        item['room_status'] = None

    return item



def _get_base_query() -> str:
    """Vrací základní SELECT s JOINy pro výpis pokojů."""
    return """
           SELECT r.*, \
                  rt.name        AS type_name, \
                  rt.base_price  AS base_price, \
                  rt.capacity    AS capacity, \
                  rt.description AS type_desc, \
                  rt.image  AS type_image_path, \
                  rs.description AS status_desc
           FROM rooms r
                    LEFT JOIN room_types rt ON r.room_type_id = rt.id
                    LEFT JOIN room_statuses rs ON r.room_status_id = rs.id \
           """


def get_room_by_id(conn: sqlite3.Connection, room_id: int) -> Optional[Dict[str, Any]]:
    sql = _get_base_query() + " WHERE r.id = ?"
    row = conn.execute(sql, (room_id,)).fetchone()
    return _map_room_full(row)


def list_rooms(conn: sqlite3.Connection, filter_status_id: int = None, filter_room_type_id: int = None) -> List[
    Dict[str, Any]]:
    sql = _get_base_query()
    params = []
    conditions = []

    # Dynamické filtrování (abychom nemuseli mít 3 různé funkce)
    if filter_status_id:
        conditions.append("r.room_status_id = ?")
        params.append(filter_status_id)

    if filter_room_type_id:
        conditions.append("r.room_type_id = ?")
        params.append(filter_room_type_id)

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY r.floor, r.number"

    rows = conn.execute(sql, params).fetchall()
    return [_map_room_full(r) for r in rows]


# Tyto funkce můžeme nechat pro zpětnou kompatibilitu,
# ale interně už volají tu chytrou list_rooms nahoře.
def list_rooms_by_status(conn: sqlite3.Connection, status_id: int) -> List[Dict[str, Any]]:
    return list_rooms(conn, filter_status_id=status_id)


def list_rooms_by_type(conn: sqlite3.Connection, room_type_id: int) -> List[Dict[str, Any]]:
    return list_rooms(conn, filter_room_type_id=room_type_id)


def create_room(conn: sqlite3.Connection, number: int, room_type_id: int, room_status_id: int, image_path: str,
                floor: int) -> Dict[str, Any]:
    cur = conn.execute(
        "INSERT INTO rooms (number, room_type_id, room_status_id, image_path, floor) VALUES (?, ?, ?, ?, ?)",
        (number, room_type_id, room_status_id, image_path, floor)
    )
    conn.commit()
    return get_room_by_id(conn, cur.lastrowid)


def update_room(conn: sqlite3.Connection, room_id: int, number: Optional[int] = None,
                room_type_id: Optional[int] = None, room_status_id: Optional[int] = None,
                image_path: Optional[str] = None, floor: Optional[int] = None) -> Optional[Dict[str, Any]]:
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
            room_type_id=ROOM_TYPE_STANDART,
            room_status_id=ROOM_STATUS_AVAILABLE,
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
