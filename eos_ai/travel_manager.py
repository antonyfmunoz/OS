"""
Travel Manager — full trip logistics management.
When a trip is detected, DEX builds a complete
travel brief and manages logistics.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv('/opt/OS/eos_ai/.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def detect_travel_event(event: dict) -> bool:
    """Detect if a calendar event involves travel."""
    title = event.get('title', event.get('summary', '')).lower()
    location = event.get('location', '').lower()
    description = event.get('description', '').lower()

    travel_signals = [
        'flight', 'hotel', 'trip', 'travel', 'conference',
        'summit', 'retreat', 'airport', 'fly', 'visiting',
    ]
    location_signals = [
        'airport', 'hotel', 'convention', 'center', 'ave',
        'blvd', 'street', 'suite', 'floor',
    ]

    return (
        any(s in title for s in travel_signals) or
        any(s in location for s in location_signals) or
        any(s in description for s in travel_signals)
    )


def build_travel_brief(
    event_title: str,
    destination: str,
    start_date: str,
    end_date: str,
    attendees: list = None,
    ctx=None,
) -> str:
    """Build a complete travel logistics brief."""
    try:
        from eos_ai.model_router import get_router, TaskType
        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        prompt = f"""You are DEX, EA to Antony Munoz.
Build a complete pre-trip brief for this travel event.

Event: {event_title}
Destination: {destination}
Dates: {start_date} to {end_date}
Attendees/context: {', '.join(attendees) if attendees else 'Solo'}
Antony is based in Portland, OR (PDT)

Create a comprehensive travel brief covering:

**Trip Overview**
- Purpose and key objectives
- Duration and key dates

**Logistics Checklist**
- [ ] Flight confirmation needed
- [ ] Hotel confirmation needed
- [ ] Ground transport (Uber/rental car)
- [ ] Travel documents check
- [ ] Currency if international

**Packing Essentials**
- Business items for this specific trip type
- Tech essentials
- Personal items

**Day-by-Day Schedule Template**
- Rough daily structure

**Pre-Trip Actions (48h before)**
- What DEX will handle
- What Antony needs to confirm

**Local Intelligence**
- Timezone and current time there
- Weather considerations
- Key venues/locations

Keep it practical and specific to this trip.
Under 400 words."""

        return router.call(model, prompt).strip()
    except Exception as e:
        logger.warning(f'[TravelManager] build_travel_brief failed: {e}')
        return f'Travel brief unavailable: {e}'


def log_trip(
    title: str,
    destination: str,
    start_date: str,
    end_date: str,
    ctx=None,
) -> bool:
    """Log a trip to Neon."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.db import get_conn
        ctx = ctx or load_context_from_env()

        with get_conn(ctx.org_id) as cur:
            cur.execute('''
                INSERT INTO events
                (org_id, event_type, payload_json, handled_by)
                VALUES (%s, %s, %s, %s)
            ''', (
                str(ctx.org_id),
                'trip',
                json.dumps({
                    'title': title,
                    'destination': destination,
                    'start_date': start_date,
                    'end_date': end_date,
                    'logged_at': datetime.now(PDT).isoformat(),
                }),
                'dex_travel',
            ))
        return True
    except Exception as e:
        logger.warning(f'[TravelManager] log_trip failed: {e}')
        return False
