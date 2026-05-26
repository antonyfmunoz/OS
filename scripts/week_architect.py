"""
Week Architect — Sunday 8pm PDT.
Reviews the coming week, identifies gaps and conflicts,
suggests structure, posts to #general.
Runs after weekly review (7pm).
"""

import os
import sys
import asyncio
import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo('America/Los_Angeles')
GENERAL_CHANNEL_ID = 1486289444830056540


async def architect_week():
    from adapters.google_workspace.gws_connector import GWSConnector
    from substrate.control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
    from substrate.state.context.context import load_context_from_env
    from adapters.models.model_router import get_router, TaskType

    ctx = load_context_from_env()
    gws = GWSConnector()
    now = datetime.now(PDT)

    try:
        events = gws.get_upcoming_events(days=7)
    except Exception:
        events = []

    try:
        pa = PortfolioAgent(ctx)
        ventures = pa.scan_all_ventures()
        binding = pa.identify_binding_constraint(ventures)
        constraint = binding.recommendation if binding else ''
        constraint_name = binding.name if binding else ''
    except Exception:
        constraint = ''
        constraint_name = ''

    router = get_router()
    model = router.route(TaskType.ANALYSIS)

    events_text = ''
    if events:
        for e in events[:15]:
            title = e.get('title', e.get('summary', 'Event'))
            start = e.get('start', '')
            if isinstance(start, dict):
                start = start.get('dateTime', start.get('date', ''))
            events_text += f'- {str(start)[:16]}: {title}\n'
    else:
        events_text = 'No events scheduled'

    prompt = f"""You are DEX, EA to Antony Munoz.

Today is Sunday {now.strftime('%B %d')}.
Portfolio binding constraint: {constraint_name} — {constraint}

Coming week calendar:
{events_text}

Design the optimal week for Antony. Consider:
- Monday: planning and deep work (no calls before noon ideally)
- Tuesday/Thursday: best days for sales calls
- Wednesday: operations and follow-ups
- Friday: wrap-up, review, prepare next week
- Protect at least 2 deep work blocks (2h minimum each)
- Batch similar activities

Return a structured week design as plain text with:
1. Day-by-day theme recommendations
2. Conflicts or issues spotted in current calendar
3. What to protect this week
4. The one action that will move the needle most (binding constraint)

Be direct. Under 300 words."""

    _day_themes = {
        0: "Monday — Planning & deep work",
        1: "Tuesday — Sales calls & outreach",
        2: "Wednesday — Operations & follow-ups",
        3: "Thursday — Sales calls & outreach",
        4: "Friday — Wrap-up & review",
    }
    det_lines = []
    for d in range(5):
        det_lines.append(f"**{_day_themes.get(d, f'Day {d}')}**")
    det_lines.append(f"\n**Binding constraint:** {constraint_name} — {constraint}")
    det_lines.append(f"\n**Calendar:** {events_text[:300]}")
    week_design = "\n".join(det_lines)

    try:
        ai_design = router.call(model, prompt).strip()
        if ai_design and len(ai_design) > 50:
            week_design = ai_design
    except Exception:
        pass

    message = (
        f'## Week Architecture — {now.strftime("%B %d")}\n\n'
        f'{week_design}\n\n'
        f'— DEX'
    )

    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            for i in range(0, len(message), 1900):
                await channel.send(message[i:i + 1900])
        await client.close()

    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        print('[WeekArchitect] DISCORD_BOT_TOKEN not set — exiting')
        return
    await client.start(discord_token)


if __name__ == '__main__':
    asyncio.run(architect_week())
