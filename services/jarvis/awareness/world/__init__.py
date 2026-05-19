"""
UMH Global Awareness — Tier 5 native capability.
Ingests news, weather, markets, and crypto into normalized GlobalEvent objects.
"""

from services.jarvis.awareness.world.schema import GlobalEvent, EventCategory, Severity
from services.jarvis.awareness.world.aggregator import GlobalAwarenessAggregator

__all__ = [
    "GlobalEvent",
    "EventCategory",
    "Severity",
    "GlobalAwarenessAggregator",
]
