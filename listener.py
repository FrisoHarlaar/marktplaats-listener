#!/usr/bin/env python3
"""
Marktplaats Price Listener — main entry point.

Polls Marktplaats for new listings matching configured queries and sends
Telegram alerts for unseen results below the configured price threshold.
"""
from __future__ import annotations

import logging
import signal
import sys
import time

from config_loader import load_config
from db import init_db, mark_seen, prune_old
from notifier import send_listing, send_startup_message
from search import fetch_new_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("listener")

_running = True


def _handle_signal(signum, frame):
    global _running
    logger.info("Shutdown signal received — stopping after current cycle.")
    _running = False


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def run_cycle(config) -> int:
    """Execute one poll cycle. Returns number of new listings found."""
    found = 0
    for query in config.queries:
        logger.info("Checking query: '%s' (max price: %s)", query.keyword, query.max_price)
        new_listings = fetch_new_listings(query)

        for listing in new_listings:
            logger.info("  → New listing: %s — %s", listing.title, listing.price_label)
            send_listing(config.telegram, listing)
            mark_seen(listing.id, query.keyword)
            found += 1

        if not new_listings:
            logger.info("  → No new listings.")

    return found


def main() -> None:
    logger.info("Loading config...")
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Config error: %s", exc)
        sys.exit(1)

    logger.info("Initialising database...")
    init_db()

    logger.info(
        "Starting listener — %d query(s), polling every %d minute(s).",
        len(config.queries),
        config.poll_interval_minutes,
    )
    send_startup_message(config.telegram, len(config.queries))

    poll_seconds = config.poll_interval_minutes * 60
    cycle = 0

    while _running:
        cycle += 1
        logger.info("--- Cycle %d ---", cycle)
        found = run_cycle(config)
        logger.info("Cycle %d complete — %d new listing(s) found.", cycle, found)

        # Prune old seen entries once a day (every 288 cycles at 5-min interval)
        if cycle % 288 == 0:
            prune_old(days=60)
            logger.info("Pruned old seen entries.")

        if _running:
            logger.info("Sleeping %d seconds until next cycle...", poll_seconds)
            # Sleep in small chunks so SIGTERM is handled quickly
            elapsed = 0
            while _running and elapsed < poll_seconds:
                time.sleep(1)
                elapsed += 1

    logger.info("Listener stopped cleanly.")


if __name__ == "__main__":
    main()
