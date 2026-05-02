"""
Fetches Marktplaats listings for a given query and filters unseen ones.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from marktplaats import SearchQuery, SortBy, SortOrder

from db import is_seen

logger = logging.getLogger(__name__)

MAX_LISTINGS_PER_POLL = 30


@dataclass
class QueryConfig:
    keyword: str
    max_price: Optional[int] = None  # in euros; None = no cap


@dataclass
class Listing:
    id: str
    title: str
    price: Optional[int]   # euro cents, None if not a fixed price
    price_label: str       # human-readable e.g. "€ 150" or "Bieden"
    link: str
    location: str
    keyword: str


def fetch_new_listings(query_cfg: QueryConfig) -> list[Listing]:
    """
    Search Marktplaats for query_cfg.keyword, apply price filter,
    and return only listings that have not been seen before.
    """
    try:
        search = SearchQuery(
            query=query_cfg.keyword,
            price_to=query_cfg.max_price,
            limit=MAX_LISTINGS_PER_POLL,
            sort_by=SortBy.DATE,
            sort_order=SortOrder.DESC,
        )
        raw_listings = search.get_listings()
    except Exception:
        logger.exception("Failed to fetch listings for query: %s", query_cfg.keyword)
        return []

    new_listings: list[Listing] = []
    for item in raw_listings:
        listing_id = _extract_id(item.link)
        if not listing_id or is_seen(listing_id):
            continue

        price_cents = _safe_price(item)
        if query_cfg.max_price is not None and price_cents is not None:
            if price_cents > query_cfg.max_price * 100:
                continue  # over budget

        new_listings.append(
            Listing(
                id=listing_id,
                title=item.title or "(geen titel)",
                price=price_cents,
                price_label=_price_label(item),
                link=item.link,
                location=_location_str(item),
                keyword=query_cfg.keyword,
            )
        )

    return new_listings


def _extract_id(link: str) -> Optional[str]:
    """Extract the numeric ad ID from a Marktplaats URL."""
    if not link:
        return None
    parts = [p for p in link.rstrip("/").split("/") if p]
    for part in reversed(parts):
        if part.startswith("a") and part[1:].isdigit():
            return part
        if part.isdigit():
            return part
    return parts[-1] if parts else None


def _safe_price(item) -> Optional[int]:
    """Return price in euro cents, or None if unavailable."""
    try:
        return int(item.price) if item.price is not None else None
    except (TypeError, ValueError):
        return None


def _price_label(item) -> str:
    """Return a human-readable price string in Dutch style."""
    try:
        price_str = item.price_as_string(lang="nl")
        return price_str if price_str else "Prijs onbekend"
    except Exception:
        return "Prijs onbekend"


def _location_str(item) -> str:
    try:
        loc = item.location
        if loc:
            city = getattr(loc, "city", None) or getattr(loc, "city_name", None)
            return str(city) if city else "Locatie onbekend"
    except Exception:
        pass
    return "Locatie onbekend"
