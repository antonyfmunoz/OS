"""Crypto adapter — CoinGecko free API, mock fallback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from services.umh.awareness.world.schema import (
    EventCategory,
    GlobalEvent,
    Severity,
)

logger = logging.getLogger(__name__)

COINGECKO_URL = "https://api.coingecko.com/api/v3/coins/markets"
DEFAULT_IDS = ["bitcoin", "ethereum", "solana", "cardano", "dogecoin"]

MOCK_EVENTS: list[dict[str, Any]] = [
    {
        "id": "bitcoin",
        "symbol": "BTC",
        "price": 104250.00,
        "change_24h": 2.14,
        "market_cap": 2_060_000_000_000,
    },
    {
        "id": "ethereum",
        "symbol": "ETH",
        "price": 2485.30,
        "change_24h": -0.87,
        "market_cap": 299_000_000_000,
    },
    {
        "id": "solana",
        "symbol": "SOL",
        "price": 172.45,
        "change_24h": 3.42,
        "market_cap": 84_000_000_000,
    },
    {
        "id": "cardano",
        "symbol": "ADA",
        "price": 0.78,
        "change_24h": 1.05,
        "market_cap": 27_500_000_000,
    },
    {
        "id": "dogecoin",
        "symbol": "DOGE",
        "price": 0.225,
        "change_24h": -1.33,
        "market_cap": 33_000_000_000,
    },
]


def _change_to_severity(pct: float) -> Severity:
    abs_pct = abs(pct)
    if abs_pct >= 10.0:
        return Severity.CRITICAL
    if abs_pct >= 5.0:
        return Severity.HIGH
    if abs_pct >= 2.0:
        return Severity.MEDIUM
    return Severity.LOW


def _fetch_coingecko(coin_ids: list[str], timeout: int) -> list[GlobalEvent]:
    """Fetch from CoinGecko free markets endpoint."""
    params = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": len(coin_ids),
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    resp = requests.get(
        COINGECKO_URL,
        params=params,
        timeout=timeout,
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()
    data = resp.json()

    events: list[GlobalEvent] = []
    for coin in data:
        price = coin.get("current_price", 0)
        change_24h = coin.get("price_change_percentage_24h", 0) or 0
        symbol = coin.get("symbol", "???").upper()
        name = coin.get("name", coin["id"])
        direction = "up" if change_24h >= 0 else "down"

        events.append(
            GlobalEvent(
                category=EventCategory.CRYPTO,
                title=f"{name} ({symbol}): ${price:,.2f} ({direction} {abs(change_24h):.2f}%)",
                summary=f"{name} trading at ${price:,.2f}, {direction} {abs(change_24h):.2f}% in 24h. Market cap: ${coin.get('market_cap', 0):,.0f}.",
                source="CoinGecko",
                source_url=f"https://www.coingecko.com/en/coins/{coin['id']}",
                timestamp=datetime.now(timezone.utc),
                severity=_change_to_severity(change_24h),
                confidence=0.95,
                symbols=[symbol],
                metadata={
                    "adapter": "crypto",
                    "coin_id": coin["id"],
                    "price_usd": price,
                    "change_24h_pct": round(change_24h, 2),
                    "market_cap": coin.get("market_cap"),
                    "volume_24h": coin.get("total_volume"),
                    "rank": coin.get("market_cap_rank"),
                },
            )
        )

    return events


def fetch(
    coin_ids: list[str] | None = None,
    timeout: int = 10,
) -> list[GlobalEvent]:
    """Fetch crypto events. Falls back to mock if CoinGecko fails."""
    coin_ids = coin_ids or DEFAULT_IDS

    try:
        events = _fetch_coingecko(coin_ids, timeout)
        if events:
            return events
    except Exception as e:
        logger.warning("CoinGecko fetch failed: %s", e)

    logger.info("Returning mock crypto data")
    events: list[GlobalEvent] = []
    for mock in MOCK_EVENTS:
        if mock["id"] not in coin_ids:
            continue
        direction = "up" if mock["change_24h"] >= 0 else "down"
        events.append(
            GlobalEvent(
                category=EventCategory.CRYPTO,
                title=f"{mock['id'].title()} ({mock['symbol']}): ${mock['price']:,.2f} ({direction} {abs(mock['change_24h']):.2f}%)",
                summary=f"{mock['id'].title()} at ${mock['price']:,.2f}, {direction} {abs(mock['change_24h']):.2f}% in 24h. Market cap: ${mock['market_cap']:,.0f}.",
                source="mock-crypto",
                timestamp=datetime.now(timezone.utc),
                severity=_change_to_severity(mock["change_24h"]),
                confidence=0.3,
                symbols=[mock["symbol"]],
                metadata={
                    "adapter": "crypto",
                    "mock": True,
                    "price_usd": mock["price"],
                    "change_24h_pct": mock["change_24h"],
                },
            )
        )
    return events
