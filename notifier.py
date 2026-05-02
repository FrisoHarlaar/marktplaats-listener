"""
Message formatting for Telegram listing alerts.
Sending is handled directly by the PTB bot in listener.py.
"""
from __future__ import annotations

from search import Listing


def format_listing(listing: Listing) -> str:
    return (
        f"🔔 *Nieuwe advertentie gevonden\\!*\n\n"
        f"🔍 Zoekopdracht: `{_escape(listing.keyword)}`\n"
        f"📦 *{_escape(listing.title)}*\n"
        f"💶 {_escape(listing.price_label)}\n"
        f"📍 {_escape(listing.location)}\n\n"
        f"[Bekijk advertentie]({listing.link})"
    )


def _escape(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))
