"""
WeekArchitect — designs the upcoming week using the Perfect Week
template as baseline, overlaid with real calendar events.
"""

import logging
from datetime import datetime
from pathlib import Path as _Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv(_Path(__file__).parent / '.env')
logger = logging.getLogger(__name__)
PDT = ZoneInfo('America/Los_Angeles')


def architect_week(ctx=None) -> str:
    """
    Design the upcoming week aligned to the Perfect Week template.
    Returns a formatted week plan string for Discord or file output.
    """
    try:
        from eos_ai.perfect_week import get_perfect_week
        from eos_ai.model_router import get_router, TaskType

        perfect_week = get_perfect_week(ctx)

        # Format perfect week for LLM context (Mon-Fri only)
        pw_text = '\n'.join(
            f'{day.capitalize()}: {data["theme"]} — {data["morning"]}'
            for day, data in perfect_week.items()
            if day not in ('saturday', 'sunday')
        )

        # Get real calendar events for the week if available
        calendar_context = ''
        try:
            from eos_ai.gws_connector import GWSConnector
            gws = GWSConnector()
            upcoming = gws.get_upcoming_events(days=7)
            if upcoming:
                event_lines = []
                for ev in upcoming[:10]:
                    start = ev.get('start', {}).get('dateTime', ev.get('start', {}).get('date', ''))
                    event_lines.append(f'- {ev.get("summary", "Untitled")}: {start}')
                calendar_context = 'Scheduled events:\n' + '\n'.join(event_lines)
        except Exception:
            pass

        router = get_router()
        model = router.route(TaskType.ANALYSIS)

        prompt = f"""Design the upcoming work week for Antony Munoz.

Antony's perfect week template:
{pw_text}

Align the week design to this template.

{calendar_context}

Current date: {datetime.now(PDT).strftime('%A, %B %d, %Y')}

Produce a concrete weekly plan:
- Day-by-day blocks (Monday through Friday)
- Protect deep work and revenue blocks
- Flag any conflicts with the perfect week template
- Include a single weekly focus (the one thing that moves the needle most)

Format clearly for Discord with bold day headers."""

        result = router.call(model, prompt, max_tokens=1200)
        return result.strip() if result else _fallback_week(perfect_week)
    except Exception as e:
        logger.warning(f'[WeekArchitect] architect_week failed: {e}')
        return _fallback_week({})


def _fallback_week(perfect_week: dict) -> str:
    """Return a simple Perfect Week display when LLM is unavailable."""
    lines = ['**📅 Week Plan (Perfect Week template):**', '']
    for day, data in perfect_week.items():
        if day in ('saturday', 'sunday'):
            continue
        lines.append(f'**{day.capitalize()} — {data.get("theme", "")}**')
        lines.append(f'AM: {data.get("morning", "")}')
        lines.append(f'PM: {data.get("afternoon", "")}')
        lines.append('')
    return '\n'.join(lines)
