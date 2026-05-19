"""Weather adapter — NOAA public API for US locations, mock fallback."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from services.jarvis.awareness.world.schema import (
    EventCategory,
    GlobalEvent,
    Severity,
)

logger = logging.getLogger(__name__)

NOAA_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
DEFAULT_LOCATION = {"lat": 45.5155, "lon": -122.6789, "name": "Portland, OR"}

MOCK_EVENTS: list[dict[str, Any]] = [
    {
        "title": "Clear skies expected",
        "summary": "High of 72°F, low of 54°F. No precipitation expected.",
        "location": "Portland, OR",
        "severity": "low",
    },
    {
        "title": "Wind advisory overnight",
        "summary": "Gusts up to 35 mph expected between 10 PM and 6 AM.",
        "location": "Portland, OR",
        "severity": "medium",
    },
]

SEVERITY_MAP = {
    "Extreme": Severity.CRITICAL,
    "Severe": Severity.HIGH,
    "Moderate": Severity.MEDIUM,
    "Minor": Severity.LOW,
}


def _fetch_noaa(lat: float, lon: float, location_name: str, timeout: int) -> list[GlobalEvent]:
    """Fetch forecast from NOAA Weather API."""
    headers = {"User-Agent": "UMH-GlobalAwareness/1.0", "Accept": "application/geo+json"}

    points_resp = requests.get(
        NOAA_POINTS_URL.format(lat=lat, lon=lon),
        headers=headers,
        timeout=timeout,
    )
    points_resp.raise_for_status()
    forecast_url = points_resp.json()["properties"]["forecast"]

    forecast_resp = requests.get(forecast_url, headers=headers, timeout=timeout)
    forecast_resp.raise_for_status()
    periods = forecast_resp.json()["properties"]["periods"][:4]

    events: list[GlobalEvent] = []
    for period in periods:
        events.append(
            GlobalEvent(
                category=EventCategory.WEATHER,
                title=f"{period['name']}: {period['shortForecast']}",
                summary=period.get("detailedForecast", period["shortForecast"])[:300],
                source="NOAA Weather API",
                source_url=forecast_url,
                timestamp=datetime.fromisoformat(period["startTime"]),
                location=location_name,
                severity=Severity.LOW,
                confidence=0.95,
                metadata={
                    "adapter": "weather",
                    "temperature": period.get("temperature"),
                    "temperature_unit": period.get("temperatureUnit"),
                    "wind_speed": period.get("windSpeed"),
                    "wind_direction": period.get("windDirection"),
                },
            )
        )

    alerts_url = f"https://api.weather.gov/alerts/active?point={lat},{lon}"
    try:
        alerts_resp = requests.get(alerts_url, headers=headers, timeout=timeout)
        alerts_resp.raise_for_status()
        for feature in alerts_resp.json().get("features", [])[:5]:
            props = feature["properties"]
            events.append(
                GlobalEvent(
                    category=EventCategory.WEATHER,
                    title=props.get("headline", props.get("event", "Weather Alert")),
                    summary=(props.get("description", "")[:300]),
                    source="NOAA Weather Alerts",
                    source_url=props.get("@id"),
                    timestamp=datetime.fromisoformat(props["effective"])
                    if props.get("effective")
                    else datetime.now(timezone.utc),
                    location=location_name,
                    severity=SEVERITY_MAP.get(props.get("severity", ""), Severity.MEDIUM),
                    confidence=0.95,
                    metadata={"adapter": "weather", "alert_type": props.get("event")},
                )
            )
    except Exception as e:
        logger.warning("NOAA alerts fetch failed: %s", e)

    return events


def fetch(
    locations: list[dict[str, Any]] | None = None,
    timeout: int = 10,
) -> list[GlobalEvent]:
    """Fetch weather events. Falls back to mock if NOAA fails."""
    locations = locations or [DEFAULT_LOCATION]
    events: list[GlobalEvent] = []
    any_success = False

    for loc in locations:
        try:
            loc_events = _fetch_noaa(loc["lat"], loc["lon"], loc["name"], timeout)
            events.extend(loc_events)
            any_success = True
        except Exception as e:
            logger.warning("Weather fetch for %s failed: %s", loc.get("name", "unknown"), e)

    if not any_success:
        logger.info("All weather fetches failed — returning mock data")
        for mock in MOCK_EVENTS:
            events.append(
                GlobalEvent(
                    category=EventCategory.WEATHER,
                    title=mock["title"],
                    summary=mock["summary"],
                    source="mock-weather",
                    location=mock["location"],
                    timestamp=datetime.now(timezone.utc),
                    severity=Severity(mock["severity"]),
                    confidence=0.3,
                    metadata={"adapter": "weather", "mock": True},
                )
            )

    return events
