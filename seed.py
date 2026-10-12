"""Load some realistic sample parts so the API has data to show off.
Run once with:  python seed.py
"""
import sqlite3

from app.database import get_connection, init_db

SAMPLE_PARTS = [
    ("PMP-4410", "Seawater cooling pump impeller", "Pumps", 1, 2, 21, "Atlantic Marine Supply"),
    ("FLT-2200", "Fuel oil filter element", "Filters", 24, 10, 7, "North Sea Parts Ltd"),
    ("VLV-0815", "Ballast system butterfly valve, DN150", "Valves", 0, 1, 45, "Offshore Valve Co"),
    ("BRG-3307", "Main engine turbocharger bearing kit", "Engine", 2, 2, 60, "Harbour Diesel Services"),
    ("SEL-1120", "Propeller shaft mechanical seal", "Propulsion", 3, 1, 30, "Atlantic Marine Supply"),
    ("ELC-0042", "Navigation light LED module", "Electrical", 12, 4, 10, "Bayline Electrical"),
]

if __name__ == "__main__":
    init_db()
    conn = get_connection()
    added = 0
    for part in SAMPLE_PARTS:
        try:
            conn.execute(
                """INSERT INTO parts (part_number, name, category, quantity_on_hand,
                                      reorder_level, lead_time_days, supplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                part,
            )
            added += 1
        except sqlite3.IntegrityError:
            pass  # already seeded
    conn.commit()
    conn.close()
    print(f"Added {added} sample parts.")
