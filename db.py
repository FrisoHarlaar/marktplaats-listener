"""
SQLite store for tracking seen listing IDs to prevent duplicate alerts.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "seen.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                listing_id  TEXT PRIMARY KEY,
                query       TEXT NOT NULL,
                seen_at     TIMESTAMP DEFAULT (datetime('now'))
            )
        """)


def is_seen(listing_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_listings WHERE listing_id = ?", (listing_id,)
        ).fetchone()
        return row is not None


def mark_seen(listing_id: str, query: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_listings (listing_id, query) VALUES (?, ?)",
            (listing_id, query),
        )


def prune_old(days: int = 60) -> None:
    """Remove entries older than `days` days to keep the DB lean."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM seen_listings WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )
