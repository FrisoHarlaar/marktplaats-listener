#!/usr/bin/env python3
"""
Marktplaats Price Listener — Telegram bot entry point.

Commands (only accepted from the configured chat_id):
  /add <zoekterm> [max:<prijs>]  — Add a search query
  /remove <zoekterm>             — Remove a search query
  /list                          — List all active queries
  /start | /help                 — Show available commands

The bot also runs a background job that polls Marktplaats every N minutes
for new listings matching the stored queries and sends alerts.
"""
from __future__ import annotations

import logging
import re
import sys

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, filters

from config_loader import load_config
from db import (
    add_query_to_db,
    init_db,
    list_queries_from_db,
    mark_seen,
    prune_old,
    remove_query_from_db,
)
from notifier import format_listing
from search import QueryConfig, fetch_new_listings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("listener")

_PRUNE_EVERY_N_JOBS = 288  # ~once per day at 5-min interval
_job_cycle_count = 0

HELP_TEXT = (
    "🔍 *Marktplaats Listener*\n\n"
    "Beschikbare commando's:\n\n"
    "`/add <zoekterm> [max:<prijs>]`\n"
    "  Voeg een zoekopdracht toe\\. Optioneel een maximale prijs in euro's\\.\n"
    "  _Voorbeeld:_ `/add iPhone 14 Pro max:700`\n\n"
    "`/remove <zoekterm>`\n"
    "  Verwijder een actieve zoekopdracht\\.\n"
    "  _Voorbeeld:_ `/remove iPhone 14 Pro`\n\n"
    "`/list`\n"
    "  Bekijk alle actieve zoekopdrachten\\.\n\n"
    "`/help`\n"
    "  Toon dit bericht\\."
)


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args_text = " ".join(context.args).strip()
    if not args_text:
        await update.message.reply_text(
            "❌ Gebruik: `/add <zoekterm> [max:<prijs>]`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    max_price: int | None = None
    keyword = args_text

    match = re.search(r"\s+max:(\d+)\s*$", args_text, re.IGNORECASE)
    if match:
        max_price = int(match.group(1))
        keyword = args_text[: match.start()].strip()

    if not keyword:
        await update.message.reply_text("❌ Geef een zoekterm op\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    added = add_query_to_db(keyword, max_price)
    if added:
        price_str = f" \\(max €{max_price}\\)" if max_price else ""
        await update.message.reply_text(
            f"✅ Toegevoegd: *{_esc(keyword)}*{price_str}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info("Query added: '%s' max=%s", keyword, max_price)
    else:
        await update.message.reply_text(
            f"⚠️ *{_esc(keyword)}* staat al in de lijst\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyword = " ".join(context.args).strip()
    if not keyword:
        await update.message.reply_text(
            "❌ Gebruik: `/remove <zoekterm>`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    removed = remove_query_from_db(keyword)
    if removed:
        await update.message.reply_text(
            f"🗑️ Verwijderd: *{_esc(keyword)}*",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info("Query removed: '%s'", keyword)
    else:
        await update.message.reply_text(
            f"⚠️ Zoekopdracht *{_esc(keyword)}* niet gevonden\\.\n"
            "Gebruik `/list` om de actieve zoekopdrachten te bekijken\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    queries = list_queries_from_db()
    if not queries:
        await update.message.reply_text(
            "📭 Geen actieve zoekopdrachten\\.\n"
            "Voeg er een toe met `/add <zoekterm>`\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = ["📋 *Actieve zoekopdrachten:*\n"]
    for q in queries:
        price_str = f" — max €{q['max_price']}" if q["max_price"] else " — geen prijslimiet"
        lines.append(f"• {_esc(q['keyword'])}{_esc(price_str)}")

    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ── Polling job ───────────────────────────────────────────────────────────────

async def job_check_listings(context: ContextTypes.DEFAULT_TYPE) -> None:
    global _job_cycle_count
    _job_cycle_count += 1

    queries = list_queries_from_db()
    if not queries:
        logger.info("No queries configured — skipping cycle.")
        return

    chat_id: int = context.job.data["chat_id"]
    found = 0

    for q_dict in queries:
        q = QueryConfig(keyword=q_dict["keyword"], max_price=q_dict["max_price"])
        logger.info("Checking: '%s' (max: %s)", q.keyword, q.max_price)
        new_listings = fetch_new_listings(q)

        for listing in new_listings:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=format_listing(listing),
                    parse_mode=ParseMode.MARKDOWN_V2,
                )
                mark_seen(listing.id, q.keyword)
                found += 1
                logger.info("  → Notified: %s — %s", listing.title, listing.price_label)
            except Exception:
                logger.exception("Failed to send listing notification.")

    logger.info("Cycle %d done — %d new listing(s).", _job_cycle_count, found)

    if _job_cycle_count % _PRUNE_EVERY_N_JOBS == 0:
        prune_old(days=60)
        logger.info("Pruned old seen entries.")


# ── Startup notification ──────────────────────────────────────────────────────

async def post_init(application: Application) -> None:
    chat_id: int = application.bot_data["chat_id"]
    queries = list_queries_from_db()
    count = len(queries)

    if count:
        body = f"Bewaakt *{count}* zoekopdracht\\(en\\)\\."
    else:
        body = "Nog geen zoekopdrachten\\.\nStuur `/add <zoekterm>` om te beginnen\\."

    await application.bot.send_message(
        chat_id=chat_id,
        text=f"🟢 *Marktplaats Listener gestart*\n{body}",
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("Loading config...")
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Config error: %s", exc)
        sys.exit(1)

    logger.info("Initialising database...")
    init_db()

    chat_id = int(config.telegram.chat_id)
    chat_filter = filters.Chat(chat_id=chat_id)
    interval_seconds = config.poll_interval_minutes * 60

    app = (
        Application.builder()
        .token(config.telegram.bot_token)
        .post_init(post_init)
        .build()
    )
    app.bot_data["chat_id"] = chat_id

    app.add_handler(CommandHandler(["start", "help"], cmd_help, filters=chat_filter))
    app.add_handler(CommandHandler("add", cmd_add, filters=chat_filter))
    app.add_handler(CommandHandler("remove", cmd_remove, filters=chat_filter))
    app.add_handler(CommandHandler("list", cmd_list, filters=chat_filter))

    app.job_queue.run_repeating(
        job_check_listings,
        interval=interval_seconds,
        first=10,
        data={"chat_id": chat_id},
        name="check_listings",
    )

    logger.info(
        "Bot started — polling every %d minute(s), chat_id=%d.",
        config.poll_interval_minutes,
        chat_id,
    )
    app.run_polling(drop_pending_updates=True)


def _esc(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))


if __name__ == "__main__":
    main()
