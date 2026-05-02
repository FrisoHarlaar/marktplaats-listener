"""
Telegram notifier: sends formatted listing alerts via the Bot API.
Uses python-telegram-bot's Bot in async mode, wrapped for synchronous callers.
"""
from __future__ import annotations

import asyncio
import logging

from telegram import Bot
from telegram.constants import ParseMode

from config_loader import TelegramConfig
from search import Listing

logger = logging.getLogger(__name__)


def send_listing(cfg: TelegramConfig, listing: Listing) -> None:
    """Send a single listing alert to the configured Telegram chat."""
    message = _format_message(listing)
    asyncio.run(_async_send(cfg.bot_token, cfg.chat_id, message))


def send_startup_message(cfg: TelegramConfig, query_count: int) -> None:
    """Send a one-time startup notification."""
    text = (
        f"🟢 *Marktplaats Listener gestart*\n"
        f"Bewaakt *{query_count}* zoekopdracht(en).\n"
        f"Je ontvangt een melding zodra er een nieuwe advertentie verschijnt."
    )
    asyncio.run(_async_send(cfg.bot_token, cfg.chat_id, text))


async def _async_send(bot_token: str, chat_id: str, text: str) -> None:
    async with Bot(token=bot_token) as bot:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=False,
            )
        except Exception:
            logger.exception("Failed to send Telegram message.")


def _format_message(listing: Listing) -> str:
    return (
        f"🔔 *Nieuwe advertentie gevonden!*\n\n"
        f"🔍 Zoekopdracht: `{listing.keyword}`\n"
        f"📦 *{listing.title}*\n"
        f"💶 {listing.price_label}\n"
        f"📍 {listing.location}\n\n"
        f"[Bekijk advertentie]({listing.link})"
    )
