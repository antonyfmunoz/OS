"""Markets adapter — yfinance for major indices/tickers, mock fallback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.umh.awareness.world.schema import (
    EventCategory,
    GlobalEvent,
    Severity,
)

logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = ["^GSPC", "^DJI", "^IXIC", "AAPL", "MSFT", "GOOGL"]

SYMBOL_NAMES = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "NASDAQ",
}

MOCK_EVENTS: list[dict[str, Any]] = [
    {"symbol": "^GSPC", "name": "S&P 500", "price": 5842.31, "change_pct": 0.47},
    {"symbol": "^DJI", "name": "Dow Jones", "price": 42891.04, "change_pct": 0.33},
    {"symbol": "^IXIC", "name": "NASDAQ", "price": 18532.67, "change_pct": 0.61},
    {"symbol": "AAPL", "name": "Apple", "price": 198.45, "change_pct": -0.12},
    {"symbol": "MSFT", "name": "Microsoft", "price": 432.10, "change_pct": 0.89},
    {"symbol": "GOOGL", "name": "Alphabet", "price": 175.23, "change_pct": 0.22},
]


def _change_to_severity(pct: float) -> Severity:
    abs_pct = abs(pct)
    if abs_pct >= 5.0:
        return Severity.CRITICAL
    if abs_pct >= 2.0:
        return Severity.HIGH
    if abs_pct >= 1.0:
        return Severity.MEDIUM
    return Severity.LOW


def _fetch_yfinance(symbols: list[str]) -> list[GlobalEvent]:
    """Fetch market data via yfinance."""
    import yfinance as yf

    events: list[GlobalEvent] = []
    tickers = yf.Tickers(" ".join(symbols))

    for symbol in symbols:
        try:
            ticker = tickers.tickers[symbol]
            info = ticker.fast_info
            price = info.last_price
            prev_close = info.previous_close

            if price is None or prev_close is None or prev_close == 0:
                continue

            change_pct = ((price - prev_close) / prev_close) * 100
            direction = "up" if change_pct >= 0 else "down"
            name = SYMBOL_NAMES.get(symbol, symbol)

            events.append(
                GlobalEvent(
                    category=EventCategory.MARKETS,
                    title=f"{name} ({symbol}): ${price:,.2f} ({direction} {abs(change_pct):.2f}%)",
                    summary=f"{name} at ${price:,.2f}, {direction} {abs(change_pct):.2f}% from previous close of ${prev_close:,.2f}.",
                    source="Yahoo Finance (yfinance)",
                    timestamp=datetime.now(timezone.utc),
                    severity=_change_to_severity(change_pct),
                    confidence=0.95,
                    symbols=[symbol],
                    metadata={
                        "adapter": "markets",
                        "price": round(price, 2),
                        "previous_close": round(prev_close, 2),
                        "change_pct": round(change_pct, 2),
                    },
                )
            )
        except Exception as e:
            logger.warning("yfinance fetch for %s failed: %s", symbol, e)

    return events


def fetch(symbols: list[str] | None = None) -> list[GlobalEvent]:
    """Fetch market events. Falls back to mock if yfinance unavailable or fails."""
    symbols = symbols or DEFAULT_SYMBOLS

    try:
        events = _fetch_yfinance(symbols)
        if events:
            return events
    except ImportError:
        logger.info("yfinance not installed — using mock market data")
    except Exception as e:
        logger.warning("Markets adapter failed: %s", e)

    logger.info("Returning mock market data")
    events: list[GlobalEvent] = []
    for mock in MOCK_EVENTS:
        direction = "up" if mock["change_pct"] >= 0 else "down"
        events.append(
            GlobalEvent(
                category=EventCategory.MARKETS,
                title=f"{mock['name']} ({mock['symbol']}): ${mock['price']:,.2f} ({direction} {abs(mock['change_pct']):.2f}%)",
                summary=f"{mock['name']} at ${mock['price']:,.2f}, {direction} {abs(mock['change_pct']):.2f}%.",
                source="mock-markets",
                timestamp=datetime.now(timezone.utc),
                severity=_change_to_severity(mock["change_pct"]),
                confidence=0.3,
                symbols=[mock["symbol"]],
                metadata={
                    "adapter": "markets",
                    "mock": True,
                    "price": mock["price"],
                    "change_pct": mock["change_pct"],
                },
            )
        )
    return events
