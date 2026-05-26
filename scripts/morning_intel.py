"""
Morning Intelligence Brief — runs at 5:45am PDT daily,
before the morning brief. Synthesizes overnight signals,
market movements, and relevant news into a concise
intelligence brief posted to #general.
"""

import os
import sys
import asyncio
import discord
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"


sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'runtime', '.env'))
load_dotenv(os.path.join(os.environ.get('UMH_ROOT') or os.environ.get('OS_ROOT') or os.environ.get('EOS_ROOT') or '/opt/OS', 'services', '.env'))

PDT = ZoneInfo("America/Los_Angeles")
GENERAL_CHANNEL_ID = 1486289444830056540


async def build_intel_brief():
    from substrate.state.context.context import load_context_from_env
    from substrate.state.storage.db import get_conn
    from adapters.models.model_router import get_router, TaskType
    from substrate.control_plane.strategy.portfolio_advisor import PortfolioAdvisor as PortfolioAgent
    import json as _json

    ctx = load_context_from_env()
    router = get_router()
    model = router.route(TaskType.ANALYSIS) or router.route(TaskType.FAST_RESPONSE)
    now = datetime.now(PDT)

    sections = []
    sections.append(f"## 🧠 Intelligence Brief — {now.strftime('%A, %B %d')}")
    sections.append("")

    # 1. Pull overnight signals from knowledge system
    try:
        with get_conn(ctx.org_id) as cur:
            cur.execute(
                """
                SELECT payload_json FROM events
                WHERE org_id = %s
                AND event_type IN (
                    'icp_signal', 'market_signal',
                    'research_output', 'intel_report'
                )
                AND created_at >= NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 10
            """,
                (str(ctx.org_id),),
            )
            rows = cur.fetchall()

        signals = []
        for r in rows:
            payload = r["payload_json"]
            if isinstance(payload, str):
                payload = _json.loads(payload)
            content = payload.get("content", payload.get("summary", ""))
            if content:
                signals.append(content[:200])
    except Exception:
        signals = []

    # 2. Pull from knowledge files
    knowledge_snippets = []
    try:
        import glob

        report_files = glob.glob(f"{_ROOT}/07_Knowledge/Reports/Market_Reports/*.md")
        report_files += glob.glob(f"{_ROOT}/07_Knowledge/ICP/*.md")
        report_files = sorted(report_files, key=os.path.getmtime, reverse=True)[:3]
        for rf in report_files:
            with open(rf) as f:
                content = f.read()[:400]
            knowledge_snippets.append(content)
    except Exception:
        pass

    # 3. Get portfolio context
    try:
        pa = PortfolioAgent(ctx)
        ventures = pa.scan_all_ventures()
        binding = pa.identify_binding_constraint(ventures)
        portfolio_context = (
            f"Binding constraint: {binding.name} — {binding.binding_constraint}"
            if binding
            else ""
        )
    except Exception:
        portfolio_context = ""

    # 4. Deterministic brief first, AI enhancement when available
    signals_text = "\n".join(signals[:5]) if signals else "No new signals overnight"
    knowledge_text = (
        "\n---\n".join(knowledge_snippets[:2]) if knowledge_snippets else ""
    )

    det_parts = []
    det_parts.append("**Signals**")
    if signals:
        for s in signals[:3]:
            det_parts.append(f"- {s[:120]}")
    else:
        det_parts.append("- No new signals overnight")
    det_parts.append("")
    if portfolio_context:
        det_parts.append(f"**Portfolio**: {portfolio_context}")
        det_parts.append("")
    if knowledge_snippets:
        det_parts.append("**Recent Intel**")
        for k in knowledge_snippets[:2]:
            det_parts.append(f"- {k[:120]}")
    brief = "\n".join(det_parts)

    try:
        prompt = f"""You are DEX, EA to Antony Munoz, founder of:
- Lyfe Institute (coaching men 18-25, $750, Instagram DMs)
- Empyrean Creative (B2B AI infrastructure)
- Antony F. Munoz (personal brand, Twitch)

Portfolio context: {portfolio_context}

Overnight signals:
{signals_text}

Recent knowledge:
{knowledge_text}

Generate a concise morning intelligence brief covering:
1. **Signals** — anything relevant from overnight data
2. **Market** — anything affecting AI infrastructure,
   coaching/education, or personal brand building
3. **Opportunities** — one specific opportunity worth acting on today
4. **Watch** — one thing to monitor

Under 200 words total. Direct. High signal only.
No fluff. If there's nothing meaningful, say so briefly."""

        ai_brief = router.call(model, prompt).strip()
        if ai_brief and len(ai_brief) > 30:
            brief = ai_brief
    except Exception:
        pass

    sections.append(brief)
    sections.append("")
    sections.append("— DEX")

    full_message = "\n".join(sections)

    # Write to Notion first, send link to Discord
    notion_url = ""
    try:
        from adapters.notion.notion_publisher import get_publisher

        publisher = get_publisher()
        notion_url = publisher.publish_intel_brief(
            content={
                "synthesis": brief,
                "signals": signals_text,
            }
        )
        if notion_url:
            print(f"[morning_intel] Intel brief → Notion: {notion_url}")
    except Exception as e:
        print(f"[morning_intel] Notion publish failed: {e}")

    # Post link to Discord (or fallback to full content)
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        channel = client.get_channel(GENERAL_CHANNEL_ID)
        if channel:
            if notion_url:
                await channel.send(f"🧠 **Intelligence Brief ready**\n{notion_url}")
            else:
                # Fallback: send full content if Notion failed
                for i in range(0, len(full_message), 1900):
                    await channel.send(full_message[i : i + 1900])
        await client.close()

    try:
        await client.start(os.getenv("DISCORD_BOT_TOKEN"))
    except Exception as e:
        print(f"[morning_intel] Discord post failed: {e}")


if __name__ == "__main__":
    asyncio.run(build_intel_brief())
