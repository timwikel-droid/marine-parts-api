"""Database setup: one SQLite table for spare parts, written in plain SQL."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "parts.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS parts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    part_number      TEXT    NOT NULL UNIQUE,
    name             TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    reorder_level    INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    lead_time_days   INTEGER NOT NULL DEFAULT 0 CHECK (lead_time_days >= 0),
    supplier         TEXT
);
CREATE INDEX IF NOT EXISTS idx_parts_category ON parts (category);
"""


def get_connection(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    # check_same_thread=False because FastAPI may use the connection
    # from a different worker thread than the one that opened it.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # lets us read rows like dicts
    return conn


def init_db(db_path: Path | str = DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
