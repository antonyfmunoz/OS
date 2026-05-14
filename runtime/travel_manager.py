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

load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
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
        from execution.runtime.model_router import get_router, TaskType
        from runtime.context import load_context_from_env as _lctx
        router = get_router()

        # Substrate-neutral traveler/home base framing from ctx.
        _ctx = ctx or _lctx()
        _traveler = (
            getattr(_ctx, 'founder_name', None)
            or getattr(_ctx, 'user_name', None)
            or 'the founder'
        )
        _home_base = getattr(_ctx, 'home_base', None) or 'their home base'

        prompt = f"""You are the EA assistant for {_traveler}.
Build a complete pre-trip brief for this travel event.

Event: {event_title}
Destination: {destination}
Dates: {start_date} to {end_date}
Attendees/context: {', '.join(attendees) if attendees else 'Solo'}
Home base: {_home_base}

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

        return router.call_with_fallback(TaskType.ANALYSIS, prompt).strip()
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
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='trip',
            payload={
                'title': title,
                'destination': destination,
                'start_date': start_date,
                'end_date': end_date,
                'logged_at': datetime.now(PDT).isoformat(),
            },
            handled_by='dex_travel',
        )
        return True
    except Exception as e:
        logger.warning(f'[TravelManager] log_trip failed: {e}')
        return False


def research_flights(
    origin: str,
    destination: str,
    date: str,
    return_date: str = '',
) -> str:
    """Research flight options (informational — no booking)."""
    try:
        from execution.runtime.model_router import get_router, TaskType
        router = get_router()

        return router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Research flight options.

From: {origin}
To: {destination}
Date: {date}
Return: {return_date or 'One way'}

Provide:
1. Typical airlines serving this route
2. Estimated flight duration
3. Typical price range
4. Best booking sites (Google Flights, Kayak, etc.)
5. Tips for this specific route
6. Recommended booking timeline

Note: This is research to help Antony make the booking.
Be specific and practical.""").strip()
    except Exception as e:
        return f'Flight research unavailable: {e}'


def research_hotels(
    city: str,
    check_in: str,
    check_out: str,
    budget_per_night: float = 200,
    preferences: str = '',
) -> str:
    """Research hotel options (informational — no booking)."""
    try:
        from execution.runtime.model_router import get_router, TaskType
        router = get_router()

        return router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Research hotel options.

City: {city}
Check-in: {check_in}
Check-out: {check_out}
Budget: ${budget_per_night}/night
Preferences: {preferences or 'Business travel, good location, reliable WiFi'}

Provide:
1. 3-4 specific hotel recommendations with names
2. Neighborhood recommendations
3. What to avoid
4. Booking tips for this city
5. Price range to expect

Note: Research only — Antony makes the final booking.""").strip()
    except Exception as e:
        return f'Hotel research unavailable: {e}'


def research_restaurants(
    city: str,
    occasion: str = 'business dinner',
    budget: str = 'moderate',
    dietary: str = '',
) -> str:
    """Research restaurant options for a city and occasion."""
    try:
        from execution.runtime.model_router import get_router, TaskType
        router = get_router()

        return router.call_with_fallback(TaskType.FAST_RESPONSE, f"""Research restaurant options.

City: {city}
Occasion: {occasion}
Budget: {budget}
Dietary needs: {dietary or 'None specified'}

Recommend 4-5 specific restaurants with:
- Name and neighborhood
- Why it fits this occasion
- Price range
- Must-order dishes
- Reservation tips

Be specific with real restaurant names.""").strip()
    except Exception as e:
        return f'Restaurant research unavailable: {e}'


def generate_trip_itinerary(
    trip_name: str,
    destination: str,
    start_date: str,
    end_date: str,
    meetings: list = None,
    hotel: str = '',
    ctx=None,
) -> str:
    """Generate a day-by-day trip itinerary document and save to Drive."""
    try:
        from execution.runtime.model_router import get_router, TaskType
        from adapters.google_workspace.gws_connector import GWSConnector
        router = get_router()

        meetings_text = '\n'.join(f'- {m}' for m in (meetings or [])) if meetings else 'No meetings confirmed yet'

        itinerary = router.call_with_fallback(TaskType.ANALYSIS, f"""Generate a detailed trip itinerary.

Trip: {trip_name}
Destination: {destination}
Dates: {start_date} to {end_date}
Hotel/Base: {hotel or 'TBD'}
Confirmed meetings:
{meetings_text}

Create:
# Trip Itinerary: {trip_name}

## Overview
## Pre-departure checklist
## Day-by-day schedule (each day from {start_date} to {end_date})
## Logistics (transport, addresses, timezone)
## Meeting prep notes
## Post-trip checklist (receipts, follow-ups, CRM updates)

Keep it practical and specific.""").strip()

        gws = GWSConnector()
        try:
            gws.create_document(
                title=f'Itinerary — {trip_name} — {start_date}',
                content=itinerary,
            )
        except Exception:
            pass

        return itinerary
    except Exception as e:
        logger.warning(f'[Travel] generate_trip_itinerary failed: {e}')
        return f'Itinerary unavailable: {e}'


def log_loyalty_program(
    program: str,
    provider: str,
    account_number: str = '',
    points_balance: int = 0,
    tier: str = '',
    ctx=None,
) -> bool:
    """Track a travel loyalty program membership."""
    try:
        from runtime.context import load_context_from_env
        from state.memory.memory import AgentMemory
        ctx = ctx or load_context_from_env()

        AgentMemory().log_event(
            org_id=str(ctx.org_id),
            event_type='loyalty_program',
            payload={
                'program': program,
                'provider': provider,
                'account_number': account_number,
                'points_balance': points_balance,
                'tier': tier,
                'updated_at': datetime.now(PDT).isoformat(),
            },
            handled_by='dex_travel',
        )
        return True
    except Exception as e:
        logger.warning(f'[Travel] log_loyalty failed: {e}')
        return False


def reconcile_trip_expenses(
    trip_name: str,
    expenses: list,
    ctx=None,
) -> dict:
    """
    Post-trip expense reconciliation.
    expenses: [{"description": str, "amount": float, "category": str}]
    """
    try:
        from runtime.expense_tracker import store_expense
        total = 0.0
        stored = 0
        for exp in expenses:
            exp_copy = {**exp, 'trip': trip_name, 'source': 'trip_reconciliation'}
            if store_expense(exp_copy, ctx):
                total += float(exp.get('amount', 0))
                stored += 1

        return {
            'trip': trip_name,
            'expenses_logged': stored,
            'total': total,
        }
    except Exception as e:
        return {'error': str(e)}
