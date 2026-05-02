"""
SQLite store for seen listing IDs (deduplication) and managed queries.
"""
import sqlite3
from pathlib import Path
from typing import Optional

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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queries (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword   TEXT NOT NULL UNIQUE,
                max_price INTEGER,
                added_at  TIMESTAMP DEFAULT (datetime('now'))
            )
        """)


# ── Seen listings ────────────────────────────────────────────────────────────

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
    """Remove seen entries older than `days` days to keep the DB lean."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM seen_listings WHERE seen_at < datetime('now', ?)",
            (f"-{days} days",),
        )


# ── Queries ───────────────────────────────────────────────────────────────────

def add_query_to_db(keyword: str, max_price: Optional[int]) -> bool:
    """Insert a query. Returns False if the keyword already exists."""
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO queries (keyword, max_price) VALUES (?, ?)",
                (keyword, max_price),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def remove_query_from_db(keyword: str) -> bool:
    """Delete a query by keyword (case-insensitive). Returns False if not found."""
    with _connect() as conn:
        result = conn.execute(
            "DELETE FROM queries WHERE keyword = ? COLLATE NOCASE", (keyword,)
        )
        return result.rowcount > 0


def list_queries_from_db() -> list[dict]:
    """Return all queries ordered by insertion time."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT keyword, max_price FROM queries ORDER BY added_at"
        ).fetchall()
        return [{"keyword": row[0], "max_price": row[1]} for row in rows]
