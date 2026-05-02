"""
Config loader: reads config.yaml and validates required fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass
class QueryConfig:
    keyword: str
    max_price: Optional[int] = None  # None means no price cap


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str


@dataclass
class Config:
    telegram: TelegramConfig
    queries: list[QueryConfig]
    poll_interval_minutes: int = 5


def load_config(path: Path = CONFIG_PATH) -> Config:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            "Copy config.example.yaml to config.yaml and fill in your values."
        )

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    tg = raw.get("telegram", {})
    if not tg.get("bot_token") or not tg.get("chat_id"):
        raise ValueError("config.yaml: telegram.bot_token and telegram.chat_id are required.")

    queries_raw = raw.get("queries", [])
    if not queries_raw:
        raise ValueError("config.yaml: at least one entry under 'queries' is required.")

    queries = [
        QueryConfig(
            keyword=q["keyword"],
            max_price=q.get("max_price"),
        )
        for q in queries_raw
    ]

    return Config(
        telegram=TelegramConfig(
            bot_token=tg["bot_token"],
            chat_id=str(tg["chat_id"]),
        ),
        queries=queries,
        poll_interval_minutes=int(raw.get("poll_interval_minutes", 5)),
    )
