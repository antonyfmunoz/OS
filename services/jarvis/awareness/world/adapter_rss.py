"""RSS adapter — fetches headlines from public RSS feeds."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

from services.jarvis.awareness.world.schema import (
    EventCategory,
    GlobalEvent,
    Severity,
)

logger = logging.getLogger(__name__)

DEFAULT_FEEDS: list[dict[str, str]] = [
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml", "name": "NYT"},
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "name": "BBC World"},
    {"url": "https://www.reddit.com/r/worldnews/.rss", "name": "Reddit r/worldnews"},
]

MOCK_EVENTS: list[dict[str, Any]] = [
    {
        "title": "Global Markets Rally on Trade Talks",
        "summary": "Major indices up 1-2% on renewed optimism.",
        "source": "mock-rss",
        "source_url": None,
        "published": None,
    },
    {
        "title": "UN Climate Summit Opens in Geneva",
        "summary": "195 nations meet to set 2030 emissions targets.",
        "source": "mock-rss",
        "source_url": None,
        "published": None,
    },
    {
        "title": "Tech Sector Layoffs Slow for Third Consecutive Month",
        "summary": "Hiring sentiment improves across major tech companies.",
        "source": "mock-rss",
        "source_url": None,
        "published": None,
    },
]


def _parse_rss_xml(content: str, feed_name: str) -> list[dict[str, Any]]:
    """Parse RSS XML using stdlib ElementTree."""
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(content)
        for item in root.iter("item"):
            title_el = item.find("title")
            desc_el = item.find("description")
            link_el = item.find("link")
            pub_el = item.find("pubDate")
            items.append(
                {
                    "title": title_el.text.strip()
                    if title_el is not None and title_el.text
                    else "Untitled",
                    "summary": (
                        desc_el.text.strip()[:300] if desc_el is not None and desc_el.text else ""
                    ),
                    "source": feed_name,
                    "source_url": link_el.text.strip()
                    if link_el is not None and link_el.text
                    else None,
                    "published": pub_el.text.strip()
                    if pub_el is not None and pub_el.text
                    else None,
                }
            )
    except ET.ParseError as e:
        logger.warning("XML parse error for %s: %s", feed_name, e)
    return items


def _try_feedparser(url: str, feed_name: str, timeout: int) -> list[dict[str, Any]] | None:
    """Attempt feedparser if available; return None if not installed."""
    try:
        import feedparser
    except ImportError:
        return None

    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "UMH-GlobalAwareness/1.0"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.text)
    items: list[dict[str, Any]] = []
    for entry in feed.entries[:10]:
        items.append(
            {
                "title": getattr(entry, "title", "Untitled"),
                "summary": getattr(entry, "summary", "")[:300],
                "source": feed_name,
                "source_url": getattr(entry, "link", None),
                "published": getattr(entry, "published", None),
            }
        )
    return items


def fetch(feeds: list[dict[str, str]] | None = None, timeout: int = 10) -> list[GlobalEvent]:
    """Fetch RSS events. Falls back to mock data if all feeds fail."""
    feeds = feeds or DEFAULT_FEEDS
    events: list[GlobalEvent] = []
    any_success = False

    for feed_cfg in feeds:
        url = feed_cfg["url"]
        name = feed_cfg["name"]
        try:
            items = _try_feedparser(url, name, timeout)
            if items is None:
                resp = requests.get(
                    url, timeout=timeout, headers={"User-Agent": "UMH-GlobalAwareness/1.0"}
                )
                resp.raise_for_status()
                items = _parse_rss_xml(resp.text, name)

            for item in items[:10]:
                events.append(
                    GlobalEvent(
                        category=EventCategory.NEWS,
                        title=item["title"],
                        summary=item["summary"],
                        source=item["source"],
                        source_url=item.get("source_url"),
                        timestamp=datetime.now(timezone.utc),
                        severity=Severity.LOW,
                        confidence=0.9,
                        metadata={"adapter": "rss", "feed_url": url},
                    )
                )
            any_success = True
        except Exception as e:
            logger.warning("RSS feed %s failed: %s", name, e)

    if not any_success:
        logger.info("All RSS feeds failed — returning mock data")
        for mock in MOCK_EVENTS:
            events.append(
                GlobalEvent(
                    category=EventCategory.NEWS,
                    title=mock["title"],
                    summary=mock["summary"],
                    source="mock-rss",
                    timestamp=datetime.now(timezone.utc),
                    severity=Severity.LOW,
                    confidence=0.3,
                    metadata={"adapter": "rss", "mock": True},
                )
            )

    return events
