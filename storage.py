"""The only persistent data: local timestamps and daily reports."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

DB = Path(__file__).with_name("attendance.sqlite3")


@contextmanager
def connection():
    db = sqlite3.connect(DB)
    try:
        with db:
            yield db
    finally:
        db.close()  # SQLite's transaction context alone does not close the handle.


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def init():
    with connection() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY, ts TEXT);
            CREATE TABLE IF NOT EXISTS reports(date TEXT PRIMARY KEY,
                                              text TEXT, created_at TEXT);
        """)


def add_visit(ts=None):
    ts = ts or now()
    with connection() as db:
        db.execute("INSERT INTO visits(ts) VALUES (?)", (ts,))
    return ts


def visits(day):
    with connection() as db:
        return [r[0] for r in db.execute(
            "SELECT ts FROM visits WHERE substr(ts,1,10)=? ORDER BY ts,id", (day,))]


def save_report(day, text):
    with connection() as db:
        db.execute("INSERT OR REPLACE INTO reports VALUES (?,?,?)", (day, text, now()))


def report(day):
    with connection() as db:
        row = db.execute("SELECT text,created_at FROM reports WHERE date=?", (day,)).fetchone()
    return {"text": row[0], "created_at": row[1]} if row else {
        "text": "Summary pending", "created_at": None}
