import sqlite3
from contextlib import contextmanager
from typing import Iterator
import os

@contextmanager
def open_connection() -> Iterator[sqlite3.Connection]:
    current_dir = os.path.dirname(os.path.realpath(__file__))
    database_path = os.path.join(current_dir, 'database.db')
    conn = sqlite3.connect(
        database_path,
        detect_types=sqlite3.PARSE_DECLTYPES,
        check_same_thread=False,   # povolí použití v jiném vlákně
    )
    conn.row_factory = sqlite3.Row
    conn.set_trace_callback(print)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    try:
        yield conn
    finally:
        conn.close()
