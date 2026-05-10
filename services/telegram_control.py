import asyncio
import subprocess
import os
import sys
import json
import glob
import datetime
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kpi_tracker
import cost_tracker

load_dotenv()

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Resolve AI name — DEX by default, user-configurable via BIS or AI_NAME env
try:
    from eos_ai.context import load_context_from_env as _load_ctx
    from eos_ai.business_instance import get_ai_name as _get_ai_name
    _AI_NAME = _get_ai_name(_load_ctx())
except Exception:
    _AI_NAME = os.getenv('AI_NAME', 'DEX')

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # target chat for scheduled briefing
VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_FILE = os.path.join(VAULT, "03_CRM/Pipeline.md")

PIPELINE_STAGES = ["New", "Contacted", "Replied", "Qualifying", "Booked", "Won", "Lost"]

# ─── Voice / meeting session state ────────────────────────────────────────────
_vi = None                      # VoiceInterface singleton (meeting sessions)
_meeting_session_id: str | None = None
_meeting_lead_name:  str | None = None  # lead name active in current meeting
_post_meeting_summary:    str   = ""    # stored for follow-up drafting
_post_meeting_next_steps: list  = []    # stored for follow-up drafting

# ─── Per-chat message ordering ────────────────────────────────────────────────
# One asyncio.Lock per chat_id ensures messages are processed strictly in
# the order they arrive — no concurrent handler execution per chat.
_chat_locks: dict[int, asyncio.Lock] = {}

# Per-chat session IDs — one continuous conversation per chat
_chat_sessions: dict[int, str] = {}


def _get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]


def parse_pipeline():
    """Read Pipeline.md and return (stage_counts dict, top_new_leads list)."""
    if not os.path.exists(PIPELINE_FILE):
        return {s: 0 for s in PIPELINE_STAGES}, []

    with open(PIPELINE_FILE, encoding="utf-8") as f:
        lines = f.readlines()

    counts = {s: 0 for s in PIPELINE_STAGES}
    new_leads = []
    current_stage = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_stage = stripped[3:].strip()
        elif stripped.startswith("- [ ]") and current_stage in counts:
            counts[current_stage] += 1
            if current_stage == "New":
                new_leads.append(stripped)

    return counts, new_leads


def format_lead_line(card):
    """Parse a kanban card line into '@username — score — archetype' for briefing."""
    try:
        display = card.split("[[")[1].split("]]")[0]
        if "|" in display:
            display = display.split("|")[1]
        rest = card.split("]]")[1].strip().lstrip(" —").strip()
        parts = [p.strip() for p in rest.split(" — ")]
        score = parts[0] if parts else "?"
        archetype = parts[1] if len(parts) > 1 else "Unknown"
        return f"- {display} — {score} — {archetype}"
    except (IndexError, Exception):
        return f"- {card[6:80]}"


def build_briefing_text():
    counts, new_leads = parse_pipeline()
    top_leads_block = "\n".join(format_lead_line(c) for c in new_leads[:5]) or "No new leads yet."

    costs = cost_tracker.get_today_costs()
    scraper = costs.get("scraper", {})
    scanned = scraper.get("apify_results", 0)
    qualified = scraper.get("haiku_calls", 0)
    scraper_cost = scraper.get("total", 0.0)

    trend = kpi_tracker.get_reply_rate_trend(days=7)
    if len(trend) >= 3:
        trend_str = " → ".join(f"{r}%" for r in trend)
        trend_block = f"TREND (7 days)\n  Reply rate: {trend_str}\n\n"
    else:
        trend_block = "TREND: Building data...\n\n"

    revenue_path = os.path.join(VAULT,
        "services/revenue_log.json")
    try:
        with open(revenue_path) as f:
            rev = json.load(f)
        month = datetime.date.today().isoformat()[:7]
        month_rev = rev["monthly"].get(month, 0.0)
        clients = len([c for c in rev["clients"]
                       if c["date"].startswith(month)])
        rev_line = (f"Revenue this month: "
                    f"${month_rev:.0f} "
                    f"({clients} clients)")
    except Exception:
        rev_line = "Revenue: $0 (no closes yet)"

    return (
        "OS Morning Briefing\n\n"
        "Pipeline:\n"
        f"  New:        {counts['New']} leads\n"
        f"  Contacted:  {counts['Contacted']} leads\n"
        f"  Replied:    {counts['Replied']} leads\n"
        f"  Booked:     {counts['Booked']} calls\n"
        f"  {rev_line}\n\n"
        f"{trend_block}"
        "Top new leads:\n"
        f"{top_leads_block}\n\n"
        "LAST NIGHT\n"
        f"  Scanned:    {scanned} comments\n"
        f"  Qualified:  {qualified} leads\n"
        f"  Cost:       ${scraper_cost:.4f}\n\n"
        "Open Pipeline.md in Obsidian to manage your board.\n"
        "Today's target: 60 DMs."
    )


async def send_morning_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = build_briefing_text()
    await update.message.reply_text(text)


async def scheduled_morning_briefing(context: ContextTypes.DEFAULT_TYPE):
    text = build_briefing_text()
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


async def scheduled_signal_scan(context: ContextTypes.DEFAULT_TYPE):
    """Scheduled reality intelligence scan — fires at 12pm and 6pm."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.reality_engine import RealityIntelligenceEngine
        ctx     = load_context_from_env()
        rie     = RealityIntelligenceEngine(ctx)
        summary = rie.process_signal_queue()
        # Only notify if any HIGH or CRITICAL signals found
        total_critical = sum(
            v.get("CRITICAL", 0) if isinstance(v, dict) else 0
            for v in summary.values()
        )
        total_high = sum(
            v.get("HIGH", 0) if isinstance(v, dict) else 0
            for v in summary.values()
        )
        if total_critical > 0 or total_high > 0:
            lines = [f"INTEL UPDATE — {datetime.datetime.now().strftime('%H:%M')}\n"]
            for venture_id, tiers in summary.items():
                if isinstance(tiers, dict) and (tiers.get("CRITICAL", 0) + tiers.get("HIGH", 0)) > 0:
                    lines.append(
                        f"{venture_id}: {tiers.get('CRITICAL', 0)} critical, "
                        f"{tiers.get('HIGH', 0)} high"
                    )
            text = "\n".join(lines)
            await context.bot.send_message(chat_id=context.job.chat_id, text=text)
    except Exception as e:
        print(f"[Telegram] Scheduled signal scan failed: {e}")


def schedule_morning_briefing(app):
    if not CHAT_ID:
        return
    if app.job_queue is None:
        print("JobQueue not available -- install with: pip install 'python-telegram-bot[job-queue]'")
        return
    app.job_queue.run_daily(
        scheduled_morning_briefing,
        time=datetime.time(hour=6, minute=0),
        chat_id=CHAT_ID,
        name="morning_briefing",
    )
    app.job_queue.run_daily(
        scheduled_eod_report,
        time=datetime.time(hour=18, minute=0),
        chat_id=CHAT_ID,
        name="eod_report",
    )
    app.job_queue.run_daily(
        midnight_snapshot,
        time=datetime.time(hour=23, minute=59),
        chat_id=CHAT_ID,
        name="midnight_snapshot",
    )
    # Reality intelligence — 12pm and 6pm signal scans
    app.job_queue.run_daily(
        scheduled_signal_scan,
        time=datetime.time(hour=12, minute=0),
        chat_id=CHAT_ID,
        name="signal_scan_noon",
    )
    app.job_queue.run_daily(
        scheduled_signal_scan,
        time=datetime.time(hour=18, minute=30),
        chat_id=CHAT_ID,
        name="signal_scan_evening",
    )


async def run_command(command, update: Update):
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True, cwd=VAULT
    )
    output = result.stdout.strip() or result.stderr.strip() or "Done. No output returned."
    if len(output) > 4096:
        output = output[:4090] + "\n..."
    await update.message.reply_text(output)


async def research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Signal research started...")
    from eos_ai.context import load_context_from_env
    from eos_ai.gateway import EOSGateway
    ctx = load_context_from_env()
    gw = EOSGateway(ctx)
    result = gw.handle({
        'type': 'agent_task',
        'team': 'research',
        'prompt': (
            "Run signal intelligence scan and "
            "generate market research summary for "
            "lyfe_institute — analyze ICP patterns, "
            "competitor moves, and emerging opportunities"
        ),
        'venture_id': 'lyfe_institute',
        'task_type': 'ANALYZE',
    })
    output = result.get('output') or result.get('brief_text') or str(result)
    await update.message.reply_text(output[:4000])


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Market report generating...")
    from eos_ai.context import load_context_from_env
    from eos_ai.gateway import EOSGateway
    ctx = load_context_from_env()
    gw = EOSGateway(ctx)
    result = gw.handle({
        'type': 'agent_task',
        'team': 'research',
        'prompt': (
            "Generate full market intelligence "
            "report for lyfe_institute — include ICP "
            "signals, market trends, and strategic "
            "recommendations"
        ),
        'venture_id': 'lyfe_institute',
        'task_type': 'ANALYZE',
    })
    output = result.get('output') or result.get('brief_text') or str(result)
    await update.message.reply_text(output[:4000])


async def content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Content engine running...")
    from eos_ai.context import load_context_from_env
    from eos_ai.gateway import EOSGateway
    ctx = load_context_from_env()
    gw = EOSGateway(ctx)
    result = gw.handle({
        'type': 'agent_task',
        'team': 'content',
        'prompt': (
            "Generate content ideas and draft "
            "posts for lyfe_institute — use latest ICP "
            "signals and market intelligence to inform "
            "hooks and angles"
        ),
        'venture_id': 'lyfe_institute',
        'task_type': 'GENERATE',
    })
    output = result.get('output') or result.get('brief_text') or str(result)
    await update.message.reply_text(output[:4000])


async def outreach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Outreach messages generating...")
    from eos_ai.context import load_context_from_env
    from eos_ai.gateway import EOSGateway
    ctx = load_context_from_env()
    gw = EOSGateway(ctx)
    result = gw.handle({
        'type': 'agent_task',
        'team': 'sales',
        'prompt': (
            "Generate outreach messages for "
            "lyfe_institute leads currently in pipeline "
            "— personalize to each lead's ICP profile "
            "and conversation stage"
        ),
        'venture_id': 'lyfe_institute',
        'task_type': 'GENERATE',
    })
    output = result.get('output') or result.get('brief_text') or str(result)
    await update.message.reply_text(output[:4000])


async def leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lead signals generating...")
    from eos_ai.context import load_context_from_env
    from eos_ai.gateway import EOSGateway
    ctx = load_context_from_env()
    gw = EOSGateway(ctx)
    result = gw.handle({
        'type': 'agent_task',
        'team': 'sales',
        'prompt': (
            "Qualify and score all leads in "
            "lyfe_institute pipeline — rank by ICP fit, "
            "engagement signals, and conversion "
            "probability"
        ),
        'venture_id': 'lyfe_institute',
        'task_type': 'SCORE',
    })
    output = result.get('output') or result.get('brief_text') or str(result)
    await update.message.reply_text(output[:4000])


async def sent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log DMs sent today. Usage: /sent <number>"""
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Usage: /sent <number>  e.g. /sent 30")
        return

    n = int(args[0])
    today = datetime.date.today().isoformat()

    data = {"date": today, "dms_sent": n}
    if os.path.exists(kpi_tracker.DAILY_LOG):
        try:
            with open(kpi_tracker.DAILY_LOG, encoding="utf-8") as f:
                existing = json.load(f)
            if existing.get("date") == today:
                data["dms_sent"] = existing.get("dms_sent", 0) + n
        except Exception:
            pass

    with open(kpi_tracker.DAILY_LOG, "w", encoding="utf-8") as f:
        json.dump(data, f)

    await update.message.reply_text(f"Logged: {data['dms_sent']} DMs sent today.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pipeline counts, cost totals, and KPI history summary."""
    counts, _ = parse_pipeline()
    total_leads = sum(counts.values())

    cost_summary = cost_tracker.get_cost_summary()
    month_total = cost_summary["month_total"]
    all_time = cost_summary["all_time_total"]

    history = []
    history_path = os.path.join(VAULT, "services/kpi_history.json")
    if os.path.exists(history_path):
        try:
            with open(history_path, encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    total_dms = sum(e.get("dms_sent", 0) for e in history)
    avg_reply = 0
    if history:
        rates = [e.get("reply_rate", 0) for e in history if e.get("dms_sent", 0) > 0]
        avg_reply = round(sum(rates) / len(rates)) if rates else 0

    revenue_path = os.path.join(VAULT,
        "services/revenue_log.json")
    try:
        with open(revenue_path) as f:
            rev = json.load(f)
        month = datetime.date.today().isoformat()[:7]
        month_rev = rev["monthly"].get(month, 0.0)
        total_rev = rev["total"]
        rev_text = (
            f"REVENUE\n"
            f"  This month: ${month_rev:.0f}\n"
            f"  All time:   ${total_rev:.0f}\n"
        )
    except Exception:
        rev_text = "REVENUE\n  No closes yet.\n"

    text = (
        "OS — Stats\n\n"
        "PIPELINE\n"
        f"  New:         {counts['New']}\n"
        f"  Contacted:   {counts['Contacted']}\n"
        f"  Replied:     {counts['Replied']}\n"
        f"  Qualifying:  {counts['Qualifying']}\n"
        f"  Booked:      {counts['Booked']}\n"
        f"  Won:         {counts['Won']}\n"
        f"  Total:       {total_leads}\n\n"
        f"{rev_text}\n"
        "KPI HISTORY\n"
        f"  Days logged:  {len(history)}\n"
        f"  Total DMs:    {total_dms}\n"
        f"  Avg reply %:  {avg_reply}%\n\n"
        "COSTS\n"
        f"  This month:  ${month_total:.2f}\n"
        f"  All time:    ${all_time:.2f}"
    )
    await update.message.reply_text(text)


async def hashtags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show hashtag performance report."""
    text = kpi_tracker.get_hashtag_report()
    await update.message.reply_text(text)


async def blacklist_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a hashtag from all groups and add to blacklist. Usage: /blacklist <tag>"""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /blacklist <tag>  e.g. /blacklist discipline")
        return

    tag = args[0].lstrip("#").lower()
    config_path = os.path.join(VAULT, "services/hashtag_config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        await update.message.reply_text("Could not read hashtag_config.json")
        return

    removed_from = []
    for group, tags in config.get("groups", {}).items():
        if tag in tags:
            config["groups"][group] = [t for t in tags if t != tag]
            removed_from.append(group)

    if tag not in config.get("blacklist", []):
        config.setdefault("blacklist", []).append(tag)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    if removed_from:
        await update.message.reply_text(f"#{tag} removed from group(s) {', '.join(removed_from)} and blacklisted.")
    else:
        await update.message.reply_text(f"#{tag} added to blacklist (was not in any group).")


async def add_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a hashtag to group A or B. Usage: /addhashtag <tag> <A|B>"""
    args = context.args
    if len(args) < 2 or args[1].upper() not in ("A", "B"):
        await update.message.reply_text("Usage: /addhashtag <tag> <A|B>  e.g. /addhashtag hustle A")
        return

    tag = args[0].lstrip("#").lower()
    group = args[1].upper()
    config_path = os.path.join(VAULT, "services/hashtag_config.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        await update.message.reply_text("Could not read hashtag_config.json")
        return

    if tag in config.get("blacklist", []):
        await update.message.reply_text(f"#{tag} is blacklisted. Remove from blacklist first.")
        return

    group_tags = config.get("groups", {}).get(group, [])
    if tag in group_tags:
        await update.message.reply_text(f"#{tag} is already in group {group}.")
        return

    config["groups"][group] = group_tags + [tag]
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    await update.message.reply_text(f"#{tag} added to group {group}.")


def move_pipeline_card_by_username(
        username, from_stage, to_stage):
    pipeline_path = os.path.join(
        VAULT, "03_CRM/Pipeline.md")
    if not os.path.exists(pipeline_path):
        return
    with open(pipeline_path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    card_line = None
    card_idx = None
    current_section = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            current_section = line[3:].strip()
        elif (current_section == from_stage and
              username.lower() in line.lower()):
            card_line = line
            card_idx = i
            break
    if card_line is None:
        return
    lines.pop(card_idx)
    for i, line in enumerate(lines):
        if line.startswith(f"## {to_stage}"):
            lines.insert(i + 3, card_line)
            break
    with open(pipeline_path, "w",
              encoding="utf-8") as f:
        f.write("\n".join(lines))


def log_call_outcome(username, outcome):
    calls_path = os.path.join(VAULT,
        "services/calls_log.json")
    try:
        with open(calls_path) as f:
            data = json.load(f)
    except Exception:
        data = {"calls": [], "showed": 0,
                "noshow": 0, "show_rate": 0.0}

    data["calls"].append({
        "username": username,
        "outcome": outcome,
        "date": datetime.date.today().isoformat()
    })
    data["showed"] = sum(
        1 for c in data["calls"]
        if c["outcome"] == "showed")
    data["noshow"] = sum(
        1 for c in data["calls"]
        if c["outcome"] == "noshow")
    total = data["showed"] + data["noshow"]
    if total > 0:
        data["show_rate"] = round(
            data["showed"] / total * 100, 1)

    with open(calls_path, "w") as f:
        json.dump(data, f, indent=2)


async def closed(update: Update,
                 context: ContextTypes.DEFAULT_TYPE):
    """Log a closed client. Usage: /closed username 750"""
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "Usage: /closed username 750\n"
            "Amount defaults to 750 if not specified.")
        return

    username = args[0].lstrip("@")
    amount = float(args[1]) if len(args) > 1 else 750.0
    today = datetime.date.today().isoformat()

    revenue_path = os.path.join(VAULT,
        "services/revenue_log.json")

    try:
        with open(revenue_path) as f:
            revenue = json.load(f)
    except Exception:
        revenue = {"clients": [], "total": 0.0,
                   "monthly": {}}

    revenue["clients"].append({
        "username": username,
        "amount": amount,
        "date": today,
        "offer": "Initiate Arena"
    })
    revenue["total"] = sum(
        c["amount"] for c in revenue["clients"])

    month = today[:7]
    if month not in revenue["monthly"]:
        revenue["monthly"][month] = 0.0
    revenue["monthly"][month] += amount

    with open(revenue_path, "w") as f:
        json.dump(revenue, f, indent=2)

    move_pipeline_card_by_username(username,
        "Booked", "Won")

    await update.message.reply_text(
        f"CLOSED\n\n"
        f"@{username} — ${amount:.0f}\n"
        f"Added to Won column.\n\n"
        f"Month total: "
        f"${revenue['monthly'][month]:.0f}\n"
        f"All time: ${revenue['total']:.0f}"
    )


async def revenue(update: Update,
                  context: ContextTypes.DEFAULT_TYPE):
    revenue_path = os.path.join(VAULT,
        "services/revenue_log.json")
    try:
        with open(revenue_path) as f:
            data = json.load(f)
    except Exception:
        await update.message.reply_text(
            "No revenue logged yet.\n"
            "Use /closed username to log a close.")
        return

    month = datetime.date.today().isoformat()[:7]
    month_rev = data["monthly"].get(month, 0.0)
    total = data["total"]
    clients = len(data["clients"])
    recent = data["clients"][-3:]

    recent_text = "\n".join([
        f"  @{c['username']} — ${c['amount']:.0f} "
        f"({c['date']})"
        for c in reversed(recent)
    ])

    await update.message.reply_text(
        f"OS — Revenue\n\n"
        f"This month: ${month_rev:.0f}\n"
        f"All time:   ${total:.0f}\n"
        f"Clients:    {clients}\n\n"
        f"Recent closes:\n{recent_text}"
    )


async def showed(update: Update,
                 context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /showed username")
        return
    username = args[0].lstrip("@")
    log_call_outcome(username, "showed")
    await update.message.reply_text(
        f"@{username} marked as showed.\n"
        f"Move to Won with /closed {username} "
        f"if they close.")


async def noshow(update: Update,
                 context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /noshow username")
        return
    username = args[0].lstrip("@")
    log_call_outcome(username, "noshow")
    move_pipeline_card_by_username(
        username, "Booked", "Lost")
    await update.message.reply_text(
        f"@{username} marked as no-show.\n"
        f"Card moved to Lost.")


async def approve_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    approval_file = os.path.join(VAULT, "services/approval_response.txt")
    with open(approval_file, "w") as f:
        f.write("approve")
    await update.message.reply_text("Approved. Scraper continuing to next tier.")


async def stop_scraper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    approval_file = os.path.join(VAULT, "services/approval_response.txt")
    with open(approval_file, "w") as f:
        f.write("stop")
    await update.message.reply_text("Stopping scraper after current batch.")


async def midnight_snapshot(context: ContextTypes.DEFAULT_TYPE):
    import kpi_history as kh

    counts = parse_pipeline()[0]
    scraper_stats = kpi_tracker.get_scraper_stats()
    daily_log = kpi_tracker.get_daily_log()
    cost_summary = cost_tracker.get_cost_summary()
    today = datetime.date.today().isoformat()

    dms = daily_log.get("dms_sent", 0)
    replies = counts.get("Replied", 0)
    rate = round(replies / max(dms, 1) * 100, 1)

    data = {
        "leads_scraped": scraper_stats.get("comments_scanned", 0),
        "leads_qualified": scraper_stats.get("qualified", 0),
        "priority_signals": scraper_stats.get("priority_signals", 0),
        "bots_filtered": scraper_stats.get("bot_filtered", 0),
        "dms_sent": dms,
        "replies_received": replies,
        "reply_rate": rate,
        "active_conversations": counts.get("Replied", 0),
        "api_cost": cost_summary.get("today_total", 0.0),
    }
    kh.update_daily(today, data)

    if datetime.date.today().weekday() == 4:  # Friday
        kh.store_weekly_rollup()


async def costs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current cost breakdown with live Apify sync."""
    try:
        cost_tracker.sync_and_update_apify_log()
    except Exception as e:
        print(f"Apify sync failed: {e}")
    text = cost_tracker.format_cost_report()
    await update.message.reply_text("OS — Cost Tracker\n\n" + text)


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manually trigger the EOD outreach report."""
    text = kpi_tracker.build_eod_report(
        kpi_tracker.get_pipeline_counts(),
        kpi_tracker.get_scraper_stats(),
        kpi_tracker.get_conversation_stats(),
        kpi_tracker.get_daily_log(),
    )
    await update.message.reply_text(text)


async def scheduled_eod_report(context: ContextTypes.DEFAULT_TYPE):
    text = kpi_tracker.build_eod_report(
        kpi_tracker.get_pipeline_counts(),
        kpi_tracker.get_scraper_stats(),
        kpi_tracker.get_conversation_stats(),
        kpi_tracker.get_daily_log(),
    )
    await context.bot.send_message(chat_id=context.job.chat_id, text=text)


# ─── Gateway-routed commands ──────────────────────────────────────────────────

async def brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/brief — AI morning brief via gateway → orchestrator."""
    await update.message.reply_text("Generating morning brief...")
    try:
        from eos_ai.gateway import EOSGateway
        gw     = EOSGateway()
        result = gw.handle({"type": "brief", "prompt": ""})
        if result.get("status") == "ok":
            text = result.get("brief", "(no brief content)")
            # Telegram 4096 char limit
            if len(text) > 4000:
                text = text[:3990] + "\n...[truncated]"
        else:
            text = f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        text = f"Gateway error: {e}"
    await update.message.reply_text(text)


async def gateway_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/research [query] — routes through gateway → research team → market_monitor."""
    query = " ".join(context.args).strip() if context.args else "analyze recent ICP signals"
    await update.message.reply_text(f"Researching: {query[:60]}...")
    try:
        from eos_ai.gateway import EOSGateway
        gw     = EOSGateway()
        result = gw.handle({
            "type":       "agent_task",
            "team":       "research",
            "sub_agent":  "market_monitor",
            "prompt":     query,
            "venture_id": "lyfe_institute",
        })
        if result.get("status") == "ok":
            text = result.get("output", "(no output)")
            if len(text) > 4000:
                text = text[:3990] + "\n...[truncated]"
        elif result.get("status") == "pending":
            text = result.get("message", "Queued for approval.")
        else:
            text = f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        text = f"Gateway error: {e}"
    await update.message.reply_text(text)


async def capture_context(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/capture [text] — store a note or decision into Neon and embed it for semantic recall."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /capture <text>\n"
            "Stores the note in Neon and embeds it for semantic search."
        )
        return
    content = ' '.join(context.args).strip()
    try:
        from eos_ai.gateway import ingest_external_context
        iid = ingest_external_context(
            source='telegram_manual',
            content=content,
            context_type='user_note',
        )
        await update.message.reply_text(
            f"Captured. ID: {iid[:8]}...\n"
            f"Now retrievable by any agent via semantic search."
        )
    except Exception as e:
        await update.message.reply_text(f"Capture failed: {e}")


async def gateway_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/approve [approval_id] — approve a queued gateway request."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /approve <approval_id>\n"
            "Use /pending to see queued requests."
        )
        return
    approval_id = context.args[0].strip()
    try:
        from eos_ai.gateway import EOSGateway
        gw     = EOSGateway()
        result = gw.approve(approval_id)
        if result.get("status") == "ok":
            text = (
                f"Approved and executed.\n\n"
                + str(result.get("output", ""))[:500]
            )
        else:
            text = f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        text = f"Gateway error: {e}"
    await update.message.reply_text(text)


async def strategy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/strategy — portfolio-level strategic analysis across all companies."""
    await update.message.reply_text("Running portfolio strategy analysis...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.strategy_engine import StrategyEngine
        ctx  = load_context_from_env()
        se   = StrategyEngine(ctx)
        data = se.analyze_portfolio_strategy()
        lines = [
            "PORTFOLIO STRATEGY\n",
            "CAPITAL ALLOCATION:",
            data.get("capital_allocation", "")[:400],
            "\nPORTFOLIO CONSTRAINT:",
            data.get("portfolio_constraint", "")[:300],
            "\nNORTH STAR PATH:",
            data.get("north_star_path", "")[:400],
        ]
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Strategy error: {e}"
    await update.message.reply_text(text)


async def decide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/decide [question] — structured 6-step decision analysis."""
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text(
            "Usage: /decide <decision question>\n"
            "Example: /decide Should I run paid ads for Initiate Arena?"
        )
        return
    await update.message.reply_text(f"Evaluating: {question[:80]}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.strategy_engine import DecisionEngine
        ctx  = load_context_from_env()
        de   = DecisionEngine(ctx)
        data = de.evaluate(
            decision=question,
            context={},
            venture_id="lyfe_institute",
        )
        lines = [
            f"DECISION: {question[:80]}\n",
            "RECOMMENDATION:",
            data.get("step6_recommendation", "")[:500],
            "\nRISK:",
            data.get("step4_risk", "")[:300],
            "\nTIMING:",
            data.get("step5_timing", "")[:300],
        ]
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Decision engine error: {e}"
    await update.message.reply_text(text)


async def gateway_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reject [approval_id] — reject a queued gateway request."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /reject <approval_id>\n"
            "Use /pending to see queued requests."
        )
        return
    approval_id = context.args[0].strip()
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.authority_engine import AuthorityEngine
        ctx    = load_context_from_env()
        ae     = AuthorityEngine(ctx)
        result = ae.reject(approval_id)
        if result.get("status") == "rejected":
            text = f"Rejected.\n\nApproval ID: {result.get('approval_id')}"
        else:
            text = f"Error: {result.get('error', 'unknown')}"
    except Exception as e:
        text = f"Gateway error: {e}"
    await update.message.reply_text(text)


async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/portfolio — board-level morning advisory across all portfolio companies."""
    await update.message.reply_text("Generating portfolio advisory...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.portfolio_advisor import PortfolioAdvisor
        ctx  = load_context_from_env()
        pa   = PortfolioAdvisor(ctx)
        text = pa.morning_advisory()
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Portfolio advisor error: {e}"
    await update.message.reply_text(text)


async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/board [question] — cross-company strategic intelligence."""
    question = " ".join(context.args).strip() if context.args else ""
    if not question:
        await update.message.reply_text("Usage: /board <question>  e.g. /board where should I focus this week?")
        return
    await update.message.reply_text(f"Analyzing across portfolio: {question[:60]}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.portfolio_advisor import PortfolioAdvisor
        ctx  = load_context_from_env()
        pa   = PortfolioAdvisor(ctx)
        text = pa.cross_company_intelligence(question)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Board advisor error: {e}"
    await update.message.reply_text(text)


async def intel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/intel — run signal scan across all ventures, return tier summary."""
    await update.message.reply_text("Scanning market signals...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.reality_engine import RealityIntelligenceEngine
        ctx     = load_context_from_env()
        rie     = RealityIntelligenceEngine(ctx)
        summary = rie.process_signal_queue()
        lines   = ["INTEL SCAN\n"]
        for venture_id, tiers in summary.items():
            if isinstance(tiers, dict) and "error" not in tiers:
                lines.append(
                    f"{venture_id}:\n"
                    f"  CRITICAL:   {tiers.get('CRITICAL', 0)}\n"
                    f"  HIGH:       {tiers.get('HIGH', 0)}\n"
                    f"  NORMAL:     {tiers.get('NORMAL', 0)}\n"
                    f"  BACKGROUND: {tiers.get('BACKGROUND', 0)}\n"
                )
            else:
                err = tiers.get("error", "unknown") if isinstance(tiers, dict) else str(tiers)
                lines.append(f"{venture_id}: ERROR — {err}\n")
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Reality engine error: {e}"
    await update.message.reply_text(text)


async def competitor_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/competitor [name] — deep competitor analysis for default venture."""
    competitor = " ".join(context.args).strip() if context.args else ""
    if not competitor:
        await update.message.reply_text(
            "Usage: /competitor <name>\n"
            "Example: /competitor 'Tony Robbins'"
        )
        return
    await update.message.reply_text(f"Analyzing competitor: {competitor[:60]}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.reality_engine import RealityIntelligenceEngine
        ctx  = load_context_from_env()
        rie  = RealityIntelligenceEngine(ctx)
        data = rie.run_competitor_analysis("lyfe_institute", competitor)
        lines = [
            f"COMPETITOR: {competitor}\n",
            "POSITIONING:",
            data.get("positioning", "")[:400],
            "\nWEAKNESSES:",
            data.get("weaknesses", "")[:300],
            "\nOPPORTUNITIES:",
            data.get("opportunities", "")[:300],
            "\nTHREAT LEVEL:",
            data.get("threat_level", "")[:100],
        ]
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Reality engine error: {e}"
    await update.message.reply_text(text)


async def truth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/truth [venture] — full competitor DNA analysis and market intelligence report."""
    venture_id = (context.args[0] if context.args else "lyfe_institute").lower().replace(" ", "_")
    await update.message.reply_text(f"Generating truth report for {venture_id}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.reality_engine import RealityIntelligenceEngine
        ctx  = load_context_from_env()
        rie  = RealityIntelligenceEngine(ctx)
        text = rie.generate_truth_report(venture_id)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Truth report error: {e}"
    await update.message.reply_text(text)


async def research_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/research [topic] — research a specific topic from first principles."""
    topic = " ".join(context.args).strip() if context.args else ""
    if not topic:
        await update.message.reply_text(
            "Usage: /research <topic>\n"
            "Example: /research Instagram DM outreach conversion rates for info products"
        )
        return
    await update.message.reply_text(f"Researching: {topic[:80]}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.research_engine import ResearchEngine
        ctx  = load_context_from_env()
        re   = ResearchEngine(ctx)
        data = re.research_topic(topic, venture_id="lyfe_institute")
        lines = [
            f"RESEARCH: {topic[:80]}\n",
            f"Confidence: {data['confidence']}\n",
            "SUMMARY:",
            data.get("summary", "")[:500],
            "\nSOURCE QUALITY:",
            data.get("sources_quality", "")[:200],
        ]
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Research engine error: {e}"
    await update.message.reply_text(text)


async def gaps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gaps — detect current knowledge gaps from interaction history."""
    await update.message.reply_text("Detecting knowledge gaps...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.research_engine import ResearchEngine
        ctx      = load_context_from_env()
        re       = ResearchEngine(ctx)
        gap_list = re.detect_knowledge_gaps()
        if gap_list:
            lines = [f"KNOWLEDGE GAPS ({len(gap_list)} detected)\n"]
            for i, gap in enumerate(gap_list, 1):
                lines.append(f"{i}. {gap}")
            text = "\n".join(lines)
        else:
            text = "No knowledge gaps detected. Run /research to build knowledge manually."
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Research engine error: {e}"
    await update.message.reply_text(text)


async def domains_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/domains — list all knowledge domains with update status."""
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.knowledge_domains import KnowledgeDomainRegistry
        registry = KnowledgeDomainRegistry()
        text = registry.get_status_report()
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Domains error: {e}"
    await update.message.reply_text(text)


async def domain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/domain [key] — show current state and principles for a specific domain."""
    key = " ".join(context.args).strip().lower().replace(" ", "_") if context.args else ""
    if not key:
        await update.message.reply_text(
            "Usage: /domain <key>\n"
            "Example: /domain business_sales\n"
            "Run /domains to see all domain keys."
        )
        return
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.knowledge_domains import KnowledgeDomainRegistry
        registry = KnowledgeDomainRegistry()
        domain = registry.get_domain(key)
        if not domain:
            available = ', '.join(sorted(registry.all_domains()))
            text = f"Domain '{key}' not found.\n\nAvailable: {available}"
        else:
            lines = [
                f"DOMAIN: {key}",
                f"Category: {domain['category']}",
                f"Update frequency: {domain.get('update_frequency', 'monthly')}",
                "\nCore principles:",
            ]
            for p in domain['core_principles']:
                lines.append(f"  • {p}")
            lines.append("\nCurrent focus:")
            for f in domain.get('current_focus', []):
                lines.append(f"  • {f}")
            # Current state from Neon
            state = registry._current_state.get(key)
            if state and state.get('content'):
                last = state.get('last_updated', '')[:10]
                lines.append(f"\nLast updated: {last}")
                lines.append("\nCurrent state (research):")
                lines.append(state['content'][:800])
            else:
                lines.append("\nNo research state saved yet.")
            text = "\n".join(lines)
            if len(text) > 4000:
                text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Domain lookup error: {e}"
    await update.message.reply_text(text)


async def trinity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/trinity — show OS Trinity status: connected products, permissions, harness profile."""
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.context import load_context_from_env
        from eos_ai.os_trinity import OSTrinity
        ctx = load_context_from_env()
        trinity = OSTrinity(ctx)
        text = trinity.format_permissions_summary(ctx.user_id)
        if len(text) > 4000:
            text = text[:3990] + '\n...[truncated]'
    except Exception as e:
        text = f'Trinity error: {e}'
    await update.message.reply_text(text)


async def connect_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/connect [product] — register a product connection (lyfeos, creatorOS, eos)."""
    product = context.args[0].strip().lower() if context.args else ''
    if not product:
        await update.message.reply_text(
            'Usage: /connect <product>\n'
            'Available: lyfeos, creatorOS, eos\n\n'
            'Phase 2: full product connections will be wired here.'
        )
        return
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.context import load_context_from_env
        from eos_ai.os_trinity import OSTrinity, VALID_PRODUCTS
        ctx = load_context_from_env()
        if product not in VALID_PRODUCTS:
            await update.message.reply_text(
                f"Unknown product '{product}'. Valid: {', '.join(VALID_PRODUCTS)}"
            )
            return
        trinity = OSTrinity(ctx)
        ok = trinity.register_product(ctx.user_id, product, {'registered_via': 'telegram'})
        text = f"Connected: {product}" if ok else f"Failed to connect {product}"
    except Exception as e:
        text = f'Connect error: {e}'
    await update.message.reply_text(text)


async def permit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/permit [source] [target] [category] — grant cross-product data permission."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            'Usage: /permit <source> <target> <category>\n'
            'Example: /permit lyfeos eos health\n'
            f'Products: lyfeos, creatorOS, eos\n'
            'Categories: health, content_performance, finance, goals, '
            'audience, habits, calendar, tasks, all'
        )
        return
    source, target, category = (
        context.args[0].lower(),
        context.args[1].lower(),
        context.args[2].lower(),
    )
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.context import load_context_from_env
        from eos_ai.os_trinity import OSTrinity
        ctx = load_context_from_env()
        trinity = OSTrinity(ctx)
        ok = trinity.grant_permission(ctx.user_id, source, target, category)
        text = (
            f"Permission granted: {source} -> {target} ({category})"
            if ok else
            f"Failed to grant permission"
        )
    except Exception as e:
        text = f'Permit error: {e}'
    await update.message.reply_text(text)


async def revoke_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/revoke [source] [target] [category] — revoke cross-product data permission."""
    if not context.args or len(context.args) < 3:
        await update.message.reply_text(
            'Usage: /revoke <source> <target> <category>\n'
            'Example: /revoke lyfeos eos health'
        )
        return
    source, target, category = (
        context.args[0].lower(),
        context.args[1].lower(),
        context.args[2].lower(),
    )
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.context import load_context_from_env
        from eos_ai.os_trinity import OSTrinity
        ctx = load_context_from_env()
        trinity = OSTrinity(ctx)
        ok = trinity.revoke_permission(ctx.user_id, source, target, category)
        text = (
            f"Permission revoked: {source} -> {target} ({category})"
            if ok else
            f"Failed to revoke permission"
        )
    except Exception as e:
        text = f'Revoke error: {e}'
    await update.message.reply_text(text)


async def aistate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/aistate — run AI landscape scan and return frontier/cost-efficient model summary."""
    await update.message.reply_text("Running AI landscape scan... (30-60s)")
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.context import load_context_from_env
        from eos_ai.research_engine import ResearchEngine
        ctx = load_context_from_env()
        re_engine = ResearchEngine(ctx)
        result = re_engine.scan_ai_landscape()

        output = result.get('output_preview', '')
        model_used = result.get('model_used', 'unknown')
        cost_updates = result.get('cost_updates', 0)

        text = (
            f"AI LANDSCAPE SCAN\n"
            f"Model used: {model_used}\n"
            f"Cost table updates: {cost_updates}\n"
            f"Domain updated: technology_ai\n\n"
            f"{output}"
        )
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"AI landscape scan error: {e}"
    await update.message.reply_text(text)


async def handle_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/errors — show recent system errors from Neon."""
    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.db import get_conn
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        with get_conn(ctx.org_id) as cur:
            cur.execute(
                """
                SELECT payload_json, created_at
                FROM events
                WHERE event_type = 'system_error' AND org_id = %s
                ORDER BY created_at DESC
                LIMIT 5
                """,
                (ctx.org_id,),
            )
            rows = cur.fetchall()
        if not rows:
            await update.message.reply_text('✅ No recent system errors')
            return
        lines = ['🔧 Recent errors:\n']
        for row in rows:
            payload = row['payload_json'] or {}
            ts = row['created_at'].strftime('%m/%d %H:%M') if row['created_at'] else '?'
            lines.append(
                f"[{ts}] {payload.get('service','?')} — {payload.get('error_type','?')}\n"
                f"  {payload.get('error','')[:100]}"
            )
        text = '\n'.join(lines)
        if len(text) > 4000:
            text = text[:3990] + '\n...[truncated]'
    except Exception as e:
        text = f'Errors query failed: {e}'
    await update.message.reply_text(text)


async def handle_outcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/outcome [type] [score] [notes] — manually log an outcome to activate RLHF."""
    _DEFAULT_SCORES = {
        'reply':  0.5,
        'booked': 1.0,
        'showed': 0.8,
        'closed': 1.0,
        'noshow': 0.0,
        'lost':   0.0,
        'opened': 0.3,
    }
    args = context.args
    if not args:
        await update.message.reply_text(
            "Usage: /outcome [type] [score] [notes]\n"
            "Types: reply | booked | showed | closed | noshow | lost | opened\n"
            "Example: /outcome closed 1.0 first Initiate Arena sale"
        )
        return

    outcome_type = args[0].lower()
    if outcome_type not in _DEFAULT_SCORES:
        await update.message.reply_text(
            f"Unknown type: {outcome_type}\n"
            f"Valid: {', '.join(_DEFAULT_SCORES.keys())}"
        )
        return

    try:
        score = float(args[1]) if len(args) > 1 else _DEFAULT_SCORES[outcome_type]
    except ValueError:
        score = _DEFAULT_SCORES[outcome_type]
    notes = ' '.join(args[2:]) if len(args) > 2 else ''

    try:
        import sys, os; sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.memory import AgentMemory
        from eos_ai.event_bus import EventBus
        mem = AgentMemory()
        outcome_id = mem.log_standalone_outcome(
            outcome_type=outcome_type,
            score=score,
            notes=notes or None,
            source='manual_telegram',
        )
        # Also publish to event bus for downstream handlers
        try:
            EventBus().publish(f'outcome_{outcome_type}', {
                'outcome_id':   outcome_id,
                'outcome_type': outcome_type,
                'score':        score,
                'notes':        notes,
                'source':       'manual_telegram',
            })
        except Exception:
            pass  # event bus is bonus — outcome is already saved

        _EMOJI = {
            'closed': '💰', 'booked': '📅', 'showed': '✅',
            'reply': '💬', 'noshow': '❌', 'lost': '❌', 'opened': '👁',
        }
        emoji = _EMOJI.get(outcome_type, '📊')
        text = (
            f"{emoji} Outcome logged\n"
            f"Type: {outcome_type}\n"
            f"Score: {score}\n"
            f"Notes: {notes or 'none'}\n\n"
            f"RLHF loop active — skill improvement engine now has signal."
        )
    except Exception as e:
        text = f"Outcome log failed: {e}"
    await update.message.reply_text(text)


async def evolve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/evolve — run the weekly evolution cycle manually."""
    await update.message.reply_text("Running evolution cycle — this may take a minute...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.evolution_engine import EvolutionEngine
        ctx     = load_context_from_env()
        ee      = EvolutionEngine(ctx)
        summary = ee.run_weekly_evolution_cycle()
        text    = ee.format_evolution_summary(summary)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Evolution engine error: {e}"
    await update.message.reply_text(text)


async def performance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/performance — analyze system performance metrics."""
    await update.message.reply_text("Analyzing system performance...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.evolution_engine import EvolutionEngine
        ctx  = load_context_from_env()
        ee   = EvolutionEngine(ctx)
        perf = ee.analyze_system_performance()
        text = ee.format_performance_report(perf)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Performance analysis error: {e}"
    await update.message.reply_text(text)


async def journey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/journey [username] — get complete lead journey from knowledge graph."""
    if not context.args:
        await update.message.reply_text("Usage: /journey <username>  e.g. /journey johndoe")
        return
    username = context.args[0].lstrip("@")
    await update.message.reply_text(f"Loading journey for @{username}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.knowledge_graph import KnowledgeGraph
        ctx  = load_context_from_env()
        kg   = KnowledgeGraph(ctx)
        data = kg.get_lead_journey(username)
        if data["total_touchpoints"] == 0:
            text = f"@{username} not found in the system.\nNo interactions logged yet."
        else:
            convs    = data["conversations"]
            outcomes = data["outcomes"]
            lines = [
                f"LEAD JOURNEY — @{username}\n",
                f"First signal:  {data['first_signal'] or 'unknown'}",
                f"Source:        {data['signal_source'] or 'unknown'}",
                f"ICP score:     {data['icp_score'] or 'not scored'}",
                f"Stage:         {data['current_stage']}",
                f"Touchpoints:   {data['total_touchpoints']}",
                f"Conversations: {len(convs)}",
                f"Outcomes:      {len(outcomes)}",
            ]
            if outcomes:
                lines.append("\nOutcomes:")
                for o in outcomes[-3:]:
                    lines.append(f"  {o['type']} (score={o['score']})")
            if convs:
                lines.append("\nLast conversation:")
                last = convs[-1]
                lines.append(f"  [{last['agent']}] {last['summary'][:150]}")
            text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Knowledge graph error: {e}"
    await update.message.reply_text(text)


async def patterns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/patterns — detect high-signal patterns from the knowledge graph."""
    await update.message.reply_text("Running pattern detection...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.knowledge_graph import KnowledgeGraph
        from eos_ai.venture_knowledge import VentureKnowledgeBase
        ctx          = load_context_from_env()
        kg           = KnowledgeGraph(ctx)
        all_patterns = []
        for vid in VentureKnowledgeBase.list_ventures():
            all_patterns.extend(kg.find_patterns(vid))
        if not all_patterns:
            text = "No patterns detected yet. Build more interaction data first."
        else:
            lines = [f"PATTERNS ({len(all_patterns)} detected)\n"]
            for i, p in enumerate(all_patterns[:8], 1):
                tier = p.get("signal_tier", "NORMAL")
                conf = p.get("confidence", 0)
                lines.append(
                    f"{i}. [{tier}] {p['description']}\n"
                    f"   Confidence: {conf:.0%} | n={p.get('sample_size', '?')}"
                )
            text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Knowledge graph error: {e}"
    await update.message.reply_text(text)


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tasks — show your pending task queue."""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.coordination_engine import CoordinationEngine
        ctx   = load_context_from_env()
        ce    = CoordinationEngine(ctx)
        queue = ce.get_task_queue()
        if not queue:
            text = "No pending tasks. Use /assign <objective> to create some."
        else:
            lines = [f"TASK QUEUE ({len(queue)} pending)\n"]
            for i, t in enumerate(queue[:10], 1):
                due = f" | due {t['due_by'][:10]}" if t.get("due_by") else ""
                lines.append(
                    f"{i}. [{t['priority'].upper()}] {t['description'][:80]}\n"
                    f"   → {t['assignee_type']}:{t['assignee_id']} | "
                    f"ID: {t['id'][:8]}{due}"
                )
            text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Coordination error: {e}"
    await update.message.reply_text(text)


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/done [task_id] — mark a task as complete."""
    if not context.args:
        await update.message.reply_text("Usage: /done <task_id>  e.g. /done a1b2c3d4")
        return
    task_id = context.args[0].strip()
    result_note = " ".join(context.args[1:]).strip() if len(context.args) > 1 else None
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.coordination_engine import CoordinationEngine
        ctx    = load_context_from_env()
        ce     = CoordinationEngine(ctx)
        result = ce.complete_task(task_id, result=result_note)
        if result.get("error"):
            text = f"Error: {result['error']}"
        else:
            desc = (result.get("description") or "")[:80]
            text = f"Task completed.\n\n{desc}"
    except Exception as e:
        text = f"Coordination error: {e}"
    await update.message.reply_text(text)


async def assign_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/assign [objective] — CEO Agent breaks objective into tasks and assigns them."""
    if not context.args:
        await update.message.reply_text(
            "Usage: /assign <objective>  "
            "e.g. /assign Follow up with leads who replied but did not book"
        )
        return
    objective = " ".join(context.args).strip()
    await update.message.reply_text(f"CEO Agent delegating: {objective[:60]}...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.coordination_engine import CoordinationEngine
        ctx    = load_context_from_env()
        ce     = CoordinationEngine(ctx)
        result = ce.ceo_delegate(
            company_objective=objective,
            venture_id="lyfe_institute",
        )
        tasks  = result.get("tasks_created", [])
        if not tasks:
            text = "No tasks generated. Try a more specific objective."
        else:
            lines = [
                f"DELEGATION COMPLETE\n",
                f"Objective: {objective[:80]}\n",
                f"Tasks created: {result['total']} "
                f"({result['ai_tasks']} AI, {result['human_tasks']} human)\n",
            ]
            for i, t in enumerate(tasks[:8], 1):
                lines.append(
                    f"{i}. [{t['priority'].upper()}] {t['description'][:70]}\n"
                    f"   → {t['executor']} | {t.get('estimated_time', '?')}"
                )
            text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"CEO delegation error: {e}"
    await update.message.reply_text(text)


async def model_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/model — view or change model routing. Usage: /model [auto|economy|performance|local|<model_name>]"""
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.model_preferences import ModelPreferences
        ctx   = load_context_from_env()
        prefs = ModelPreferences(ctx)
    except Exception as e:
        await update.message.reply_text(f"Model preferences error: {e}")
        return

    arg = context.args[0].strip().lower() if context.args else ""

    if not arg:
        text = prefs.get_current_summary()
    elif arg == 'local':
        prefs.set_prefer_local(True)
        prefs.set_cost_mode('free')
        text = "Local/free mode active"
    elif arg == 'performance':
        prefs.set_prefer_local(False)
        prefs.set_cost_mode('performance')
        text = "Performance mode active"
    elif arg == 'economy':
        prefs.set_prefer_local(False)
        prefs.set_cost_mode('economy')
        text = "Economy mode active"
    elif arg == 'auto':
        prefs.set_prefer_local(False)
        prefs.set_cost_mode('auto')
        text = "Auto mode — routing based on business context"
    else:
        # Treat as model name — set session override
        prefs.set_session_override(arg)
        text = f"Using {arg} for this session"

    if len(text) > 4000:
        text = text[:3990] + "\n...[truncated]"
    await update.message.reply_text(text)


async def gateway_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pending — list all queued approval requests."""
    try:
        from eos_ai.gateway import EOSGateway
        gw      = EOSGateway()
        pending = gw.get_pending_approvals()
        if not pending:
            text = "No pending approvals."
        else:
            lines = [f"Pending approvals ({len(pending)}):"]
            for p in pending:
                aid   = p.get("approval_id", "?")
                ptype = p.get("type", "?")
                agent = p.get("sub_agent") or p.get("action") or "—"
                ts    = (p.get("queued_at") or "")[:19]
                lines.append(f"\n  ID:     {aid}")
                lines.append(f"  Type:   {ptype} / {agent}")
                lines.append(f"  Queued: {ts}")
                lines.append(f"  Prompt: {p.get('prompt', '')[:60]}")
            text = "\n".join(lines)
    except Exception as e:
        text = f"Gateway error: {e}"
    await update.message.reply_text(text)


VOICE_TRIGGERS = [
    'speak', 'say this', 'voice response',
    'read this', 'tell me', 'say it',
    'voice', 'talk to me', 'speak to me',
]


def wants_voice_response(text: str) -> bool:
    text_lower = text.lower()
    return any(t in text_lower for t in VOICE_TRIGGERS)


def _get_vi(ctx) -> 'VoiceInterface':
    """Lazy-init VoiceInterface singleton for meeting sessions."""
    global _vi
    if _vi is None:
        from eos_ai.voice_interface import VoiceInterface
        _vi = VoiceInterface(ctx)
    return _vi


# ── GWS commands ──────────────────────────────────────────────────────────────

async def calendar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/calendar — today's events + this week."""
    try:
        import sys
        sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.gws_connector import GWSConnector
        gws = GWSConnector()

        today   = gws.get_today_events()
        week    = gws.get_upcoming_events(days=7)

        lines = ["📅 TODAY"]
        if today:
            for e in today:
                start_str = (e["start"] or "")[:16]
                lines.append(f"  {start_str} — {e['title']}")
                if e.get("meet_link"):
                    lines.append(f"  🎥 {e['meet_link']}")
        else:
            lines.append("  No events today")

        lines.append("\n📆 THIS WEEK")
        if week:
            for e in week:
                start_str = (e["start"] or "")[:16]
                lines.append(f"  {start_str} — {e['title']}")
        else:
            lines.append("  No upcoming events")

        text = "\n".join(lines)
    except Exception as e:
        text = f"Calendar error: {e}"
    await update.message.reply_text(text[:4096])


async def gtasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gtasks — Google Tasks list."""
    try:
        import sys
        sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.gws_connector import GWSConnector
        gws   = GWSConnector()
        tasks = gws.get_tasks()
        if tasks:
            lines = [f"✅ TASKS ({len(tasks)} pending)"]
            for t in tasks[:20]:
                due = f" | due {t['due'][:10]}" if t.get("due") else ""
                lines.append(f"  • {t['title']}{due}")
            text = "\n".join(lines)
        else:
            text = "✅ TASKS\nNo pending tasks"
    except Exception as e:
        text = f"Tasks error: {e}"
    await update.message.reply_text(text[:4096])


async def gmail_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/gmail — last 5 email subjects + senders."""
    try:
        import sys
        sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
        from eos_ai.gws_connector import GWSConnector
        gws    = GWSConnector()
        emails = gws.get_recent_emails(max_results=5)
        if emails:
            lines = [f"📬 GMAIL ({len(emails)} recent)"]
            for e in emails:
                lines.append(f"  {e['from'][:40]}")
                lines.append(f"  → {e['subject'][:60]}")
                if e.get("snippet"):
                    lines.append(f"  {e['snippet'][:80]}")
                lines.append("")
            text = "\n".join(lines).strip()
        else:
            text = "📬 GMAIL\nNo recent emails"
    except Exception as e:
        text = f"Gmail error: {e}"
    await update.message.reply_text(text[:4096])


_meeting_type: str = 'sales_call'  # active meeting type


_MEETING_TYPES = {
    'sales_call', 'content_planning', 'ops_review', 'finance_review',
    'team_standup', 'weekly_review', 'strategy_session', 'vendor_call',
    'investor_update', 'coaching_session', 'research_session',
}


async def meeting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/meeting [type] [attendee] | /meeting end — type-aware meeting sessions."""
    global _vi, _meeting_session_id, _meeting_lead_name, _meeting_type
    global _post_meeting_summary, _post_meeting_next_steps

    args   = context.args
    subcmd = args[0].lower() if args else ''

    # /meeting end
    if subcmd == 'end':
        if not _meeting_session_id:
            await update.message.reply_text('No active meeting session.')
            return
        await update.message.reply_text('Processing meeting transcript...')
        try:
            from eos_ai.context import load_context_from_env
            ctx = load_context_from_env()
            vi  = _get_vi(ctx)

            # Use type-aware end if available
            try:
                result = vi.end_meeting_with_actions(
                    _meeting_session_id, _meeting_type, 'lyfe_institute'
                )
            except AttributeError:
                result = vi.end_meeting_session(_meeting_session_id)

            _post_meeting_summary    = result.get('summary', '')
            _post_meeting_next_steps = result.get('next_steps', [])

            lines = [f'MEETING COMPLETE — {_meeting_type.replace("_", " ").upper()}\n']
            if result['summary']:
                lines.append(f'SUMMARY:\n{result["summary"][:400]}\n')
            if result['decisions']:
                lines.append('DECISIONS:')
                for d in result['decisions'][:6]:
                    lines.append(f'  • {d}')
                lines.append('')
            if result['action_items']:
                lines.append('ACTION ITEMS:')
                for a in result['action_items'][:6]:
                    lines.append(f"  • {a['owner']}: {a['action']}")
                lines.append('')
            if result['next_steps']:
                lines.append('NEXT STEPS:')
                for s in result['next_steps'][:5]:
                    lines.append(f'  • {s}')

            text = '\n'.join(lines)
            if len(text) > 4000:
                text = text[:3990] + '\n...[truncated]'
            await update.message.reply_text(text)

            # Post-meeting automation (sales calls get full chain)
            if _meeting_type == 'sales_call':
                lead = _meeting_lead_name or 'unknown'
                await _run_post_meeting_automation(
                    ctx=ctx,
                    lead_name=lead,
                    summary=result.get('summary', ''),
                    action_items=result.get('action_items', []),
                    next_steps=result.get('next_steps', []),
                    bot=context.bot,
                    chat_id=update.message.chat_id,
                )
            elif result.get('post_action'):
                await context.bot.send_message(
                    chat_id=update.message.chat_id,
                    text=f"Post-meeting: {result['post_action']}",
                )

        except Exception as e:
            await update.message.reply_text(f'Meeting end error: {e}')
        finally:
            _meeting_session_id = None
            _meeting_lead_name  = None
            _meeting_type       = 'sales_call'
            _vi                 = None

        return

    # /meeting start [lead] — backward compat → sales_call
    if subcmd == 'start':
        meeting_type = 'sales_call'
        attendee     = ' '.join(args[1:]).strip() or 'Meeting'
    # /meeting [type] [attendee]
    elif subcmd in _MEETING_TYPES:
        meeting_type = subcmd
        attendee     = ' '.join(args[1:]).strip() or meeting_type.replace('_', ' ').title()
    else:
        available = '\n'.join(f'  /meeting {t}' for t in sorted(_MEETING_TYPES))
        await update.message.reply_text(
            'Usage:\n'
            '/meeting [type] [attendee] — start meeting\n'
            '/meeting end               — end session\n\n'
            f'Types:\n{available}\n\n'
            'Mid-meeting shortcuts (text only):\n'
            '  score · objections · history · stage · numbers'
        )
        return

    # Start the meeting
    _meeting_type = meeting_type
    from eos_ai.context import load_context_from_env
    ctx = load_context_from_env()
    vi  = _get_vi(ctx)
    _meeting_session_id = vi.start_meeting_session(
        f'{meeting_type}: {attendee}'
    )
    _meeting_lead_name = attendee
    # Store active type on VoiceInterface for during-meeting lookups
    vi._active_meeting_type = meeting_type

    await update.message.reply_text(
        f'Meeting started: {meeting_type.replace("_", " ").upper()}\n'
        f'Attendee: {attendee}\n'
        f'Session: {_meeting_session_id[:8]}...\n\n'
        f'Send voice to capture. /meeting end when done.\n'
        f'Text shortcuts: score, objections, history, stage, numbers\n\n'
        f'Preparing brief...'
    )

    # Pre-meeting brief
    try:
        from eos_ai.voice_interface import VoiceInterface
        brief = vi.get_meeting_brief(
            meeting_type=meeting_type,
            venture_id='lyfe_institute',
            attendee_context={'name': attendee} if attendee else None,
        )
        await update.message.reply_text(brief[:4000])
    except AttributeError:
        # Fallback for sales_call: use existing automation
        if meeting_type == 'sales_call':
            try:
                agenda = await _run_pre_meeting_automation(
                    ctx=ctx,
                    lead_name=attendee,
                    bot=context.bot,
                    chat_id=update.message.chat_id,
                )
                await update.message.reply_text(agenda)
            except Exception as e:
                await update.message.reply_text(f'Agenda prep failed: {e}')
    except Exception as e:
        await update.message.reply_text(f'Brief failed: {e}')


# ─── /sync — force full system sync ──────────────────────────────────────────

async def handle_backfill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/backfill — read all connected integrations and build the knowledge base."""
    venture = (context.args[0] if context.args else "lyfe_institute").strip()
    await update.message.reply_text(
        f"Running onboarding backfill for {venture}...\n"
        "This reads Drive, Gmail, Calendar, Tasks, and CRM.\n"
        "Will take 30-60 seconds."
    )
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.onboarding_backfill import OnboardingBackfill
        ctx = load_context_from_env()
        ob  = OnboardingBackfill(ctx)
        ob.run_full_backfill(venture)
        await update.message.reply_text(ob.get_backfill_status())
    except Exception as e:
        await update.message.reply_text(f"Backfill error: {e}")


async def handle_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sync — force reload all components: skills, user model, domains, profiles."""
    await update.message.reply_text("Running full sync...")
    results = []

    # 1. Reload skill registry
    try:
        from eos_ai.skill_registry import SkillRegistry
        SkillRegistry._instance = None
        sr = SkillRegistry()
        results.append(f"Skills: {len(sr._skills)} loaded")
    except Exception as e:
        results.append(f"Skills: error — {e}")

    # 2. Update user model
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.user_model import UserModel
        ctx = load_context_from_env()
        um = UserModel(ctx)
        um.maybe_update_profile()
        trust = um.get_trust_level()
        results.append(f"User model: trust={trust}")
    except Exception as e:
        results.append(f"User model: error — {e}")

    # 3. Sync user model to harness
    try:
        from eos_ai.os_trinity import OSTrinity
        trinity = OSTrinity(ctx)
        synced = trinity.sync_from_user_model(ctx.user_id)
        results.append(f"Harness profile: {'synced' if synced else 'no change'}")
    except Exception as e:
        results.append(f"Harness profile: error — {e}")

    # 4. Refresh domain registry
    try:
        from eos_ai.knowledge_domains import KnowledgeDomainRegistry
        registry = KnowledgeDomainRegistry()
        due = registry.get_update_schedule()
        results.append(f"Domains: {len(due)} due for update")
    except Exception as e:
        results.append(f"Domains: error — {e}")

    # 5. Reload human profiles for all CRM leads
    try:
        from eos_ai.human_intelligence import HumanIntelligenceEngine
        hie = HumanIntelligenceEngine(ctx)
        profile_result = hie.profile_all_crm_leads()
        results.append(
            f"Leads: {profile_result.get('leads_processed', 0)} processed, "
            f"{profile_result.get('profiles_written', 0)} refreshed"
        )
    except Exception as e:
        results.append(f"Leads: error — {e}")

    summary = "Sync complete\n" + "\n".join(f"  • {r}" for r in results)
    await update.message.reply_text(summary)


# ─── Multimodal media handler ─────────────────────────────────────────────────

async def handle_media_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Handle voice, video, photo, audio, and document messages."""
    from eos_ai.context import load_context_from_env
    from eos_ai.cognitive_loop import CognitiveLoop, MultimodalInput
    from eos_ai.agent_runtime import TaskType

    msg     = update.message
    chat_id = msg.chat_id
    lock    = _get_chat_lock(chat_id)
    await lock.acquire()
    file_obj = None
    modality = 'unknown'
    suffix = '.bin'

    if msg.voice:
        file_obj = await msg.voice.get_file()
        suffix = '.ogg'
        modality = 'voice'

    elif msg.video or msg.video_note:
        v = msg.video or msg.video_note
        file_obj = await v.get_file()
        suffix = '.mp4'
        modality = 'video'

    elif msg.photo:
        file_obj = await msg.photo[-1].get_file()
        suffix = '.jpg'
        modality = 'image'

    elif msg.audio:
        file_obj = await msg.audio.get_file()
        suffix = '.mp3'
        modality = 'audio'

    elif msg.document:
        doc = msg.document
        fname = doc.file_name or 'file.bin'
        suffix = Path(fname).suffix or '.bin'
        file_obj = await doc.get_file()
        from eos_ai.media_processor import MediaProcessor
        modality = MediaProcessor().detect_modality(f'file{suffix}')
        if modality == 'unknown':
            lock.release()
            await msg.reply_text(
                f'File type {suffix} not supported yet.'
            )
            return

    if not file_obj:
        lock.release()
        return

    status_map = {
        'voice':    '🎙 Transcribing...',
        'video':    '🎬 Analyzing video...',
        'image':    '🖼 Analyzing image...',
        'audio':    '🔊 Processing audio...',
        'document': '📄 Reading document...',
    }
    await msg.reply_text(
        status_map.get(modality, '⏳ Processing...')
    )

    # download file to temp path
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        tmp_path = f.name
    await file_obj.download_to_drive(tmp_path)

    # convert OGG voice → WAV for Whisper
    final_path = tmp_path
    if modality == 'voice' and suffix == '.ogg':
        wav_path = tmp_path.replace('.ogg', '.wav')
        result = subprocess.run(
            ['ffmpeg', '-i', tmp_path, wav_path, '-y'],
            capture_output=True,
        )
        if result.returncode == 0:
            os.unlink(tmp_path)
            final_path = wav_path
        # if ffmpeg fails, proceed with original ogg

    caption = msg.caption or ''

    media_input = MultimodalInput(
        file_path=final_path,
        modality=modality,
        user_prompt=caption or None,
    )

    ctx = load_context_from_env()

    reply = ''
    try:
        if modality in ('voice', 'audio'):
            if _meeting_session_id:
                # Meeting capture mode — transcribe only, no synthesis
                vi = _get_vi(ctx)
                meeting_result = vi.process_meeting_audio(
                    final_path, _meeting_session_id
                )
                await msg.reply_text(
                    f'🎙 Captured: "{meeting_result["transcript"][:200]}"'
                )
            else:
                # Normal voice turn — full process_voice_turn
                from eos_ai.voice_interface import VoiceInterface
                vi   = VoiceInterface(ctx)
                turn = vi.process_voice_turn(final_path)

                audio_out  = turn['response_audio_path']
                transcript = turn['transcript']

                if audio_out and os.path.exists(audio_out):
                    with open(audio_out, 'rb') as af:
                        await msg.reply_voice(af)
                    try:
                        os.unlink(audio_out)
                    except Exception:
                        pass

                if transcript:
                    await msg.reply_text(f'🎙 You: "{transcript}"')

                if not audio_out:
                    # Synthesis failed — send text response instead
                    text_out = turn['response_text']
                    if transcript:
                        text_out = f'🎙 "{transcript}"\n\n{text_out}'
                    await msg.reply_text(text_out[:4000])

        else:
            # Non-voice media — existing CognitiveLoop path
            loop = CognitiveLoop(ctx)
            cognitive_result = loop.run(
                input=media_input,
                agent='research_agent',
                task_type=TaskType.ANALYZE,
                venture_id='lyfe_institute',
            )
            reply = cognitive_result.output or 'Could not process this media'

    except Exception as e:
        reply = f'Processing error: {str(e)}'
    finally:
        try:
            os.unlink(final_path)
        except Exception:
            pass

    lock.release()
    if reply:
        await msg.reply_text(reply[:4000])


# ─── Natural language routing ─────────────────────────────────────────────────

def check_model_triggers(text: str, prefs) -> str | None:
    """
    Pure string matching — no AI call.
    Returns a response string if a model control trigger matched, else None.
    """
    lower = text.lower().strip()

    _FREE = [
        'go local', 'use local', 'free mode', 'local models',
        'run local', 'stay local', 'use local models', 'switch to local',
    ]
    _PERFORMANCE = [
        'use best', 'performance mode', 'best models',
        'use best models', 'full power', 'no limits', 'use the best',
    ]
    _ECONOMY = [
        'economy mode', 'save costs', 'cheap mode',
        'save money', 'be cheap', 'cost mode',
    ]
    _AUTO = [
        'auto mode', 'automatic', 'let the system decide',
        'default mode', 'reset mode',
    ]
    _CLEAR = [
        'reset model', 'clear model', 'default model',
        'clear override', 'reset override',
    ]
    _WHAT = [
        'what model', 'which model', 'model status',
        'what ai', 'which ai', 'what are you using',
        'which model are you',
    ]

    if any(t in lower for t in _FREE):
        prefs.set_prefer_local(True)
        prefs.set_cost_mode('free')
        return "Local mode active — using free local models for all tasks"

    if any(t in lower for t in _PERFORMANCE):
        prefs.set_prefer_local(False)
        prefs.set_cost_mode('performance')
        return "Performance mode — best model per task"

    if any(t in lower for t in _ECONOMY):
        prefs.set_prefer_local(False)
        prefs.set_cost_mode('economy')
        return "Economy mode — Haiku and local only for routine tasks"

    if any(t in lower for t in _AUTO):
        prefs.set_cost_mode('auto')
        return "Auto mode — routing based on business context"

    if any(t in lower for t in _CLEAR) or (
        lower.startswith('stop using ') and len(lower) > 11
    ):
        prefs.set_session_override(None)
        return "Model override cleared — back to automatic selection"

    if any(t in lower for t in _WHAT):
        return prefs.get_current_summary()

    # "use <model>" or "switch to <model>"
    extracted: str | None = None
    if lower.startswith('use '):
        extracted = lower[4:].strip()
    elif lower.startswith('switch to '):
        extracted = lower[10:].strip()

    if extracted and len(extracted) > 0 and len(extracted.split()) <= 3:
        # Looks like a model name, not a sentence
        prefs.set_session_override(extracted)
        return f"Using {extracted} for this session"

    return None


async def handle_natural_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """Catch-all handler for non-command text messages."""
    text = update.message.text
    if not text or text.startswith('/'):
        return

    # Acquire per-chat lock — ensures messages are processed top-to-bottom
    # in the order they arrive, even if the user sends multiple quickly.
    chat_id = update.message.chat_id
    lock    = _get_chat_lock(chat_id)
    await lock.acquire()
    try:

        from eos_ai.context import load_context_from_env
        from eos_ai.model_preferences import ModelPreferences
        from eos_ai.gateway import EOSGateway

        ctx   = load_context_from_env()
        prefs = ModelPreferences(ctx)
        gw    = EOSGateway()
    except Exception as e:
        lock.release()
        await update.message.reply_text(f"Init error: {e}")
        return

    # Step 0: during-meeting shortcuts — text only, silent to call
    if _meeting_session_id:
        _MEETING_SHORTCUTS = {
            'score', 'icp score', 'icp',
            'objections', 'likely objections',
            'history', 'dm history', 'lead history',
            'stage', 'current stage',
            'numbers', 'kpis', 'metrics', 'revenue',
        }
        text_lower = text.lower().strip()
        if text_lower in _MEETING_SHORTCUTS or any(
            text_lower.startswith(s) for s in ('score ', 'history ', 'objection')
        ):
            try:
                vi = _get_vi(ctx)
                meeting_type = getattr(vi, '_active_meeting_type', 'sales_call')
                answer = vi.get_during_meeting_context(
                    meeting_type=meeting_type,
                    query=text,
                    session_id=_meeting_session_id,
                    venture_id='lyfe_institute',
                )
                lock.release()
                await update.message.reply_text(answer[:2000])
                return
            except Exception as e:
                lock.release()
                await update.message.reply_text(f'Meeting query error: {e}')
                return

    # Step 1: model control triggers (no AI call)
    model_response = check_model_triggers(text, prefs)
    if model_response:
        if len(model_response) > 4000:
            model_response = model_response[:4000] + '\n\n[truncated]'
        lock.release()
        await update.message.reply_text(model_response)
        return

    # Get or create per-chat session_id — preserves conversation continuity
    import uuid as _uuid_mod
    global _chat_sessions
    if chat_id not in _chat_sessions:
        _chat_sessions[chat_id] = str(_uuid_mod.uuid4())
    _session_id = _chat_sessions[chat_id]
    _channel    = 'telegram'

    # Step 2: classify intent via Haiku
    await update.message.reply_text("...")
    intent = gw.classify_intent(text)

    # Step 3: route by intent
    result: str | dict = "No response generated."
    try:
        if intent == 'BRIEF':
            result = gw.handle({
                'type': 'brief', 'prompt': text,
                'session_id': _session_id, 'channel': _channel,
            })

        elif intent == 'STRATEGY':
            result = gw.handle_ordered({
                'type':       'agent_task',
                'prompt':     text,
                'venture_id': 'lyfe_institute',
                'task_type':  'strategy',
                'session_id': _session_id,
                'channel':    _channel,
            })

        elif intent == 'OUTREACH':
            result = gw.handle_ordered({
                'type':       'agent_task',
                'team':       'sales',
                'sub_agent':  'icp_qualifier',
                'prompt':     text,
                'venture_id': 'lyfe_institute',
                'session_id': _session_id,
                'channel':    _channel,
            })

        elif intent == 'RESEARCH':
            result = gw.handle_ordered({
                'type':       'agent_task',
                'team':       'research',
                'sub_agent':  'market_monitor',
                'prompt':     text,
                'venture_id': 'lyfe_institute',
                'session_id': _session_id,
                'channel':    _channel,
            })

        elif intent == 'CONTENT':
            result = gw.handle_ordered({
                'type':       'agent_task',
                'team':       'content',
                'sub_agent':  'hook_generator',
                'prompt':     text,
                'venture_id': 'lyfe_institute',
                'session_id': _session_id,
                'channel':    _channel,
            })

        elif intent == 'DECISION':
            from eos_ai.strategy_engine import DecisionEngine
            de   = DecisionEngine(ctx)
            data = de.evaluate(
                decision=text,
                context=prefs.get_business_context(),
                venture_id='lyfe_institute',
            )
            result = (
                data.get('step6_recommendation', '')
                or data.get('recommendation', '')
                or str(data)
            )

        elif intent == 'TASK':
            from eos_ai.coordination_engine import CoordinationEngine
            ce         = CoordinationEngine(ctx)
            delegation = ce.ceo_delegate(text, 'lyfe_institute')
            tasks      = delegation.get('tasks_created', [])
            lines      = [
                f"Delegated: {delegation.get('total', len(tasks))} tasks",
                f"AI:        {delegation.get('ai_tasks', 0)}",
                f"Human:     {delegation.get('human_tasks', 0)}",
            ]
            for i, t in enumerate(tasks[:6], 1):
                lines.append(
                    f"\n{i}. [{t.get('priority','?').upper()}] "
                    f"{t.get('description','')[:70]}"
                )
            result = '\n'.join(lines)

        elif intent == 'INTEL':
            from eos_ai.reality_engine import RealityIntelligenceEngine
            rie     = RealityIntelligenceEngine(ctx)
            summary = rie.process_signal_queue()
            lines   = ["INTEL SCAN\n"]
            for vid, tiers in summary.items():
                if isinstance(tiers, dict) and 'error' not in tiers:
                    c = tiers.get('CRITICAL', 0)
                    h = tiers.get('HIGH', 0)
                    if c + h > 0:
                        lines.append(
                            f"{vid}: {c} critical, {h} high"
                        )
            result = '\n'.join(lines) if len(lines) > 1 else "No critical/high signals."

        elif intent == 'PORTFOLIO':
            from eos_ai.portfolio_advisor import PortfolioAdvisor
            pa     = PortfolioAdvisor(ctx)
            result = pa.morning_advisory()

        elif intent == 'JOURNAL':
            try:
                from eos_ai.memory import AgentMemory
                mem = AgentMemory()
                mem.log_event(
                    org_id=ctx.org_id,
                    event_type='founder_journal',
                    payload={'text': text, 'source': 'telegram'},
                )
            except Exception:
                pass  # log attempt is best-effort
            result = "Logged ✓"

        elif intent == 'MODEL':
            result = prefs.get_current_summary()

        else:  # UNKNOWN — free chat via CEO agent
            result = gw.handle_ordered({
                'type':       'agent_task',
                'prompt':     text,
                'session_id': _session_id,
                'channel':    _channel,
                'venture_id': 'lyfe_institute',
                'task_type':  'analyze',
            })

    except Exception as e:
        result = f"Error ({intent}): {e}"

    # Multi-part result — send each part in sequence
    if isinstance(result, list):
        total = len(result)
        lock.release()
        for i, part_result in enumerate(result):
            part_text = (
                part_result.get('output')
                or part_result.get('brief')
                or part_result.get('brief_text')
                or part_result.get('message')
                or str(part_result)
            )
            if not isinstance(part_text, str):
                part_text = str(part_text)
            if total > 1:
                part_text = f"[{i + 1}/{total}]\n\n{part_text}"
            if len(part_text) > 4000:
                part_text = part_text[:4000] + '\n\n[truncated]'
            await update.message.reply_text(part_text)
        return

    # Normalize single result to string
    if isinstance(result, dict):
        result = (
            result.get('output')
            or result.get('brief')
            or result.get('brief_text')
            or result.get('message')
            or str(result)
        )

    if not isinstance(result, str):
        result = str(result)

    if len(result) > 4000:
        result = result[:4000] + '\n\n[truncated]'

    if wants_voice_response(text):
        from eos_ai.media_processor import MediaProcessor
        mp = MediaProcessor()
        audio_path = mp.synthesize_speech(result)
        if audio_path:
            lock.release()
            with open(audio_path, 'rb') as af:
                await update.message.reply_voice(af)
            try:
                os.unlink(audio_path)
            except Exception:
                pass
            return

    lock.release()
    await update.message.reply_text(result)


# ─── Execution Engine commands ────────────────────────────────────────────────

async def executions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/executions — show all in-progress tasks with runtime and stuck flag."""
    try:
        from eos_ai.execution_engine import ExecutionEngine
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        ee  = ExecutionEngine(ctx)
        active = ee.get_active_executions()

        if not active:
            await update.message.reply_text("No active executions.")
            return

        lines = [f"ACTIVE EXECUTIONS ({len(active)})\n"]
        for ex in active:
            stuck_flag = " ⚠️ STUCK" if ex["stuck"] else ""
            lines.append(
                f"{'━' * 16}\n"
                f"Task: {ex['description']}\n"
                f"Agent: {ex['agent'] or '?'}\n"
                f"Running: {ex['runtime_minutes']}m{stuck_flag}\n"
                f"ID: {ex['task_id'][:8]}"
            )

        await update.message.reply_text("\n".join(lines)[:4000])
    except Exception as e:
        await update.message.reply_text(f"Executions error: {e}")


async def trace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/trace [task_id] — show full lifecycle trace for a task."""
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /trace [task_id_prefix]")
        return

    task_prefix = args[0].strip()
    try:
        from eos_ai.db import get_conn
        from eos_ai.execution_engine import ExecutionEngine
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()

        # Resolve partial task_id to full UUID
        task_id = None
        with get_conn(ctx.org_id) as cur:
            cur.execute(
                "SELECT id FROM tasks WHERE org_id = %s AND id::text LIKE %s LIMIT 1",
                (ctx.org_id, f"{task_prefix}%"),
            )
            row = cur.fetchone()
            if row:
                task_id = str(row["id"])

        if not task_id:
            await update.message.reply_text(f"No task found with ID prefix: {task_prefix}")
            return

        ee    = ExecutionEngine(ctx)
        trace = ee.get_execution_trace(task_id)

        if not trace:
            await update.message.reply_text(f"No trace found for task {task_id[:8]}")
            return

        lines = [f"EXECUTION TRACE — {task_id[:8]}\n"]
        for event in trace:
            ts = str(event.get("timestamp", ""))[:16]
            lines.append(f"[{ts}] {event['event'].upper()}")
            for k, v in event.items():
                if k not in ("event", "timestamp") and v:
                    lines.append(f"  {k}: {str(v)[:80]}")

        await update.message.reply_text("\n".join(lines)[:4000])
    except Exception as e:
        await update.message.reply_text(f"Trace error: {e}")


# ─── Business Instance commands ───────────────────────────────────────────────

async def stage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stage — current venture stage, focus, and next actions."""
    try:
        from eos_ai.business_instance import BusinessInstanceManager
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        bim = BusinessInstanceManager(ctx)
        g = bim.get_stage_guidance('lyfe_institute')
        actions = '\n'.join(f'  • {a}' for a in g['next_actions'])
        text = (
            f"STAGE {g['current_stage']}/6 — {g['stage_name']}\n\n"
            f"FOCUS: {g['focus']}\n\n"
            f"NEXT ACTIONS:\n{actions}\n\n"
            f"PROOF TO ADVANCE:\n  {g['proof_needed']}"
        )
    except Exception as e:
        text = f"Stage error: {e}"
    await update.message.reply_text(text)


async def bis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/bis — full Business Instance summary for Lyfe Institute."""
    try:
        from eos_ai.business_instance import BusinessInstanceManager
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        bim = BusinessInstanceManager(ctx)
        text = bim.format_full_summary('lyfe_institute')
        if len(text) > 4000:
            text = text[:3990] + '\n...[truncated]'
    except Exception as e:
        text = f"BIS error: {e}"
    await update.message.reply_text(text)


async def pulse_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pulse — run a live world pulse scan and integrate findings."""
    await update.message.reply_text("Scanning world pulse...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.world_pulse import WorldPulse
        ctx   = load_context_from_env()
        wp    = WorldPulse(ctx)
        pulse = wp.run_pulse_scan()
        lines = [
            f"WORLD PULSE COMPLETE",
            f"Integrated: {pulse['total_integrated']} items\n",
        ]
        for summary in pulse['sources_scanned']:
            lines.append(f"• {summary}")
        text = '\n'.join(lines)
        if len(text) > 4000:
            text = text[:3990] + '\n...[truncated]'
    except Exception as e:
        text = f"Pulse error: {e}"
    await update.message.reply_text(text)


async def advance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/advance [proof] — advance Lyfe Institute to next stage."""
    proof_text = ' '.join(context.args).strip() if context.args else ''
    if not proof_text:
        await update.message.reply_text(
            "Usage: /advance [proof of completion]\n"
            "Example: /advance First sale closed — @username paid $750"
        )
        return
    try:
        from eos_ai.business_instance import BusinessInstanceManager
        from eos_ai.context import load_context_from_env
        ctx = load_context_from_env()
        bim = BusinessInstanceManager(ctx)
        result = bim.advance_stage('lyfe_institute', {'proof': proof_text})
        if result['advanced']:
            g = result['guidance']
            text = (
                f"STAGE ADVANCED\n"
                f"Now: Stage {result['new_stage']} — {result['new_stage_name']}\n\n"
                f"New focus: {g['focus']}\n"
                f"Next proof: {g['proof_needed']}"
            )
        else:
            text = f"Cannot advance: {result['reason']}"
    except Exception as e:
        text = f"Advance error: {e}"
    await update.message.reply_text(text)


async def _run_pre_meeting_automation(
    ctx,
    lead_name: str,
    bot,
    chat_id: int,
) -> str:
    """
    Pre-meeting automation chain — runs when /meeting start [lead-name] fires.
    1. Create calendar event with Meet link (if none exists)
    2. Pull lead profile + DM history from knowledge graph
    3. Generate structured call agenda via sales agent
    4. Return formatted agenda string for Telegram
    """
    meet_link  = ""
    icp_score  = "?"
    dm_summary = ""

    # Step 0a — Calendar event
    try:
        from eos_ai.gws_connector import GWSConnector
        gws   = GWSConnector()
        event = gws.create_calendar_event(
            title=f"Sales Call — {lead_name}",
            duration_minutes=60,
            description=f"Initiate Arena sales call with @{lead_name}",
        )
        if event and event.get("meet_link"):
            meet_link = event["meet_link"]
    except Exception as e:
        print(f"[PreMeeting] Calendar event failed: {e}")

    # Pull lead data from knowledge graph
    try:
        from eos_ai.knowledge_graph import KnowledgeGraph
        kg      = KnowledgeGraph(ctx)
        journey = kg.get_lead_journey(lead_name)
        if journey.get("icp_score"):
            icp_score = str(journey["icp_score"])
        convs = journey.get("conversations", [])
        if convs:
            dm_summary = convs[-1].get("summary", "")[:250]
    except Exception as e:
        print(f"[PreMeeting] Lead journey failed: {e}")

    # Step 0b — Generate agenda via sales closer agent
    call_guidance = ""
    try:
        from eos_ai.agent_teams import run_team_task
        prompt = (
            f"Lead: @{lead_name}\n"
            f"ICP Score: {icp_score}\n"
            f"DM history: {dm_summary or 'No prior DMs captured'}\n\n"
            "Generate a structured sales call agenda: "
            "best opener question, core problem to diagnose, "
            "most likely objection and how to reframe it, "
            "and the recommended close move."
        )
        result = run_team_task(
            team="sales", sub_agent="closer",
            prompt=prompt,
            venture_id="lyfe_institute", ctx=ctx,
        )
        call_guidance = (result.get("output") or "")[:600]
    except Exception as e:
        print(f"[PreMeeting] Agenda generation failed: {e}")

    lines = [
        f"CALL AGENDA: {lead_name}",
        f"ICP Score: {icp_score}",
        f"DM history: {dm_summary or 'None on file'}",
    ]
    if call_guidance:
        lines.append(f"\n{call_guidance}")
    if meet_link:
        lines.append(f"\nMeeting link: {meet_link}")
    else:
        lines.append("\nMeeting link: (create manually or share existing)")

    return "\n".join(lines)


async def _run_post_meeting_automation(
    ctx,
    lead_name: str,
    summary: str,
    action_items: list,
    next_steps: list,
    bot,
    chat_id: int,
) -> None:
    """
    Post-meeting automation chain — runs within 5 min of /meeting end.
    8b. Outcome prompt via Telegram
    8c. Follow-up message draft
    8d. CRM lead file update
    (8e email deferred until /outcome is logged)
    """
    # Step 8b — Outcome prompt
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"CALL OUTCOME — @{lead_name}\n\n"
                "Reply with one command:\n"
                "  /outcome closed 1.0 [notes]\n"
                "  /outcome follow_up 0.5 [notes]\n"
                "  /outcome noshow 0.0"
            ),
        )
    except Exception as e:
        print(f"[PostMeeting] Outcome prompt failed: {e}")

    # Step 8c — Follow-up draft
    try:
        from eos_ai.agent_teams import run_team_task
        fu_prompt = (
            f"Lead: @{lead_name}\n"
            f"Meeting summary: {summary[:300]}\n"
            f"Next steps agreed: {', '.join(next_steps[:3]) or 'none captured'}\n\n"
            "Draft a personalized post-call follow-up message. "
            "Reference what was discussed. One clear next step."
        )
        fu_result = run_team_task(
            team="sales", sub_agent="follow_up_sequencer",
            prompt=fu_prompt,
            venture_id="lyfe_institute", ctx=ctx,
        )
        fu_text = (fu_result.get("output") or "").strip()
        if fu_text:
            await bot.send_message(
                chat_id=chat_id,
                text=f"FOLLOW-UP DRAFT\n\n{fu_text[:1200]}",
            )
    except Exception as e:
        print(f"[PostMeeting] Follow-up draft failed: {e}")

    # Step 8d — CRM update
    try:
        import glob as _glob
        _crm_root = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"
        crm_pattern = f"{_crm_root}/03_CRM/Leads/lead_{lead_name}_*.md"
        matches = sorted(_glob.glob(crm_pattern))
        if matches:
            lead_file = matches[-1]
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(lead_file, "a", encoding="utf-8") as f:
                f.write(f"\n---\n## Meeting Notes — {ts}\n")
                f.write(f"**Summary:** {summary[:400]}\n")
                if action_items:
                    f.write("\n**Action items:**\n")
                    for a in action_items[:5]:
                        f.write(f"- {a.get('owner','?')}: {a.get('action','')}\n")
                if next_steps:
                    f.write("\n**Next steps:**\n")
                    for s in next_steps[:3]:
                        f.write(f"- {s}\n")
            await bot.send_message(
                chat_id=chat_id,
                text=f"CRM updated: lead_{lead_name}",
            )
    except Exception as e:
        print(f"[PostMeeting] CRM update failed: {e}")


async def standup_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/standup — AI-generated structured team standup across all active systems."""
    await update.message.reply_text("Running standup...")
    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.coordination_engine import CoordinationEngine
        from eos_ai.cognitive_loop import CognitiveLoop
        from eos_ai.agent_runtime import TaskType
        from eos_ai.memory import AgentMemory

        ctx   = load_context_from_env()
        ce    = CoordinationEngine(ctx)
        loop  = CognitiveLoop(ctx)

        # Pull recent tasks for context
        queue = ce.get_task_queue()
        today_active  = [t for t in queue if t.get("status") in ("in_progress", "pending")]
        pipeline_counts, _ = parse_pipeline()

        standup_prompt = (
            f"Generate a structured team standup for {_AI_NAME}.\n\n"
            f"PIPELINE STATE:\n"
            f"  New: {pipeline_counts.get('New', 0)} leads\n"
            f"  Contacted: {pipeline_counts.get('Contacted', 0)}\n"
            f"  Replied: {pipeline_counts.get('Replied', 0)}\n"
            f"  Booked: {pipeline_counts.get('Booked', 0)}\n\n"
            f"ACTIVE TASKS ({len(today_active)}):\n"
            + "\n".join(
                f"  - [{t.get('priority','?').upper()}] {t.get('description','')[:70]}"
                for t in today_active[:6]
            ) + "\n\n"
            "For each department (Sales, Research, Marketing, CustomerSuccess, Ops):\n"
            "1. What was completed in the last 24h?\n"
            "2. What is the focus today?\n"
            "3. Any blockers or signals needing attention?\n\n"
            "Format as a tight standup briefing."
        )

        result = loop.run(
            input=standup_prompt,
            agent="ceo_agent",
            task_type=TaskType.ANALYZE,
            venture_id="lyfe_institute",
        )
        text = result.output or "No standup generated."

        # Log to Neon
        try:
            mem = AgentMemory()
            mem.log_event(
                org_id=ctx.org_id,
                event_type="standup",
                payload={"summary": text[:800], "source": "telegram"},
            )
        except Exception:
            pass

        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Standup error: {e}"
    await update.message.reply_text(text)


async def review_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/review — weekly business review: KPIs, binding constraint, pending decisions."""
    await update.message.reply_text("Running weekly review... (30-60s)")
    lines = ["WEEKLY BUSINESS REVIEW\n"]

    try:
        from eos_ai.context import load_context_from_env
        from eos_ai.portfolio_advisor import PortfolioAdvisor
        from eos_ai.strategy_engine import StrategyEngine
        from eos_ai.coordination_engine import CoordinationEngine
        from eos_ai.memory import AgentMemory

        ctx = load_context_from_env()

        # Portfolio Advisor — venture-level KPIs and advisory
        try:
            pa      = PortfolioAdvisor(ctx)
            advisory = pa.morning_advisory()
            lines.append("PORTFOLIO ADVISORY")
            lines.append(advisory[:600])
            lines.append("")
        except Exception as e:
            lines.append(f"Portfolio: {e}")

        # Strategy Engine — binding constraint
        try:
            se   = StrategyEngine(ctx)
            data = se.analyze_portfolio_strategy()
            constraint = data.get("portfolio_constraint", "")
            cap_alloc  = data.get("capital_allocation", "")
            if constraint:
                lines.append("BINDING CONSTRAINT")
                lines.append(constraint[:400])
                lines.append("")
            if cap_alloc:
                lines.append("CAPITAL ALLOCATION")
                lines.append(cap_alloc[:300])
                lines.append("")
        except Exception as e:
            lines.append(f"Strategy: {e}")

        # Pending decisions (high-priority tasks + pipeline)
        try:
            ce    = CoordinationEngine(ctx)
            queue = ce.get_task_queue()
            high  = [t for t in queue if t.get("priority") in ("high", "critical")]
            if high:
                lines.append(f"PENDING DECISIONS ({len(high)})")
                for t in high[:5]:
                    lines.append(
                        f"  [{t.get('priority','?').upper()}] {t.get('description','')[:70]}"
                    )
                lines.append("")
        except Exception as e:
            lines.append(f"Decisions: {e}")

        # Pipeline snapshot
        counts, _ = parse_pipeline()
        lines.append("PIPELINE")
        for stage in ("New", "Contacted", "Replied", "Qualifying", "Booked", "Won"):
            lines.append(f"  {stage:12s} {counts.get(stage, 0)}")

        text = "\n".join(lines)

        # Log to Neon
        try:
            mem = AgentMemory()
            mem.log_event(
                org_id=ctx.org_id,
                event_type="weekly_review",
                payload={"summary": text[:800], "source": "telegram"},
            )
        except Exception:
            pass

        if len(text) > 4000:
            text = text[:3990] + "\n...[truncated]"
    except Exception as e:
        text = f"Review error: {e}"
    await update.message.reply_text(text)


async def handle_browser_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """/browser [url] [task] — run a browser agent on any URL."""
    parts = update.message.text.split(' ', 2)
    if len(parts) < 3:
        await update.message.reply_text(
            'Usage: /browser [url] [task]\n'
            'Example: /browser https://notion.so "find the OS Dashboard page"'
        )
        return
    url  = parts[1]
    task = parts[2]
    await update.message.reply_text(
        f'\U0001f310 Browser agent starting...\nURL: {url}\nTask: {task}'
    )
    try:
        from eos_ai.browser_agent import run_browser_task
        result = await run_browser_task(url, task)
        steps  = '\n'.join(
            f'  \u2022 {s}' for s in result.get('steps_taken', [])
        )
        reply = (
            f'\u2705 Browser task complete\n'
            f'Steps:\n{steps or "  (none)"}\n'
            f'Final URL: {result.get("final_url", "")}'
        )
    except Exception as e:
        reply = f'\u274c Browser agent error: {e}'
    await update.message.reply_text(reply)


# ─── App setup ────────────────────────────────────────────────────────────────

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("gresearch", gateway_research))
app.add_handler(CommandHandler("market", market))
app.add_handler(CommandHandler("content", content))
app.add_handler(CommandHandler("outreach", outreach))
app.add_handler(CommandHandler("leads", leads))
app.add_handler(CommandHandler("briefing", send_morning_briefing))
app.add_handler(CommandHandler("brief", brief))
app.add_handler(CommandHandler("sent", sent))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("costs", costs))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("hashtags", hashtags))
app.add_handler(CommandHandler("blacklist", blacklist_tag))
app.add_handler(CommandHandler("addhashtag", add_hashtag))
app.add_handler(CommandHandler("capture", capture_context))
app.add_handler(CommandHandler("approve", gateway_approve))
app.add_handler(CommandHandler("reject", gateway_reject))
app.add_handler(CommandHandler("stop", stop_scraper))
app.add_handler(CommandHandler("closed", closed))
app.add_handler(CommandHandler("revenue", revenue))
app.add_handler(CommandHandler("showed", showed))
app.add_handler(CommandHandler("noshow", noshow))
app.add_handler(CommandHandler("pending", gateway_pending))
app.add_handler(CommandHandler("portfolio", portfolio))
app.add_handler(CommandHandler("board", board))
app.add_handler(CommandHandler("strategy", strategy))
app.add_handler(CommandHandler("decide", decide))
app.add_handler(CommandHandler("intel", intel))
app.add_handler(CommandHandler("competitor", competitor_cmd))
app.add_handler(CommandHandler("truth", truth))
app.add_handler(CommandHandler("research", research_cmd))
app.add_handler(CommandHandler("gaps", gaps))
app.add_handler(CommandHandler("domains", domains_cmd))
app.add_handler(CommandHandler("domain", domain_cmd))
app.add_handler(CommandHandler("aistate", aistate_cmd))
app.add_handler(CommandHandler("trinity", trinity_cmd))
app.add_handler(CommandHandler("connect", connect_cmd))
app.add_handler(CommandHandler("permit", permit_cmd))
app.add_handler(CommandHandler("revoke", revoke_cmd))
app.add_handler(CommandHandler("errors", handle_errors))
app.add_handler(CommandHandler("outcome", handle_outcome))
app.add_handler(CommandHandler("evolve", evolve))
app.add_handler(CommandHandler("performance", performance))
app.add_handler(CommandHandler("journey", journey))
app.add_handler(CommandHandler("patterns", patterns))
app.add_handler(CommandHandler("tasks", tasks_cmd))
app.add_handler(CommandHandler("done", done_cmd))
app.add_handler(CommandHandler("assign", assign_cmd))
app.add_handler(CommandHandler("model", model_cmd))
app.add_handler(CommandHandler("meeting", meeting_cmd))
app.add_handler(CommandHandler("calendar", calendar_cmd))
app.add_handler(CommandHandler("gtasks", gtasks_cmd))
app.add_handler(CommandHandler("gmail", gmail_cmd))
app.add_handler(CommandHandler("sync", handle_sync))
app.add_handler(CommandHandler("backfill", handle_backfill))
app.add_handler(CommandHandler("executions", executions_cmd))
app.add_handler(CommandHandler("trace", trace_cmd))
app.add_handler(CommandHandler("stage", stage_cmd))
app.add_handler(CommandHandler("bis", bis_cmd))
app.add_handler(CommandHandler("advance", advance_cmd))
app.add_handler(CommandHandler("pulse", pulse_cmd))
app.add_handler(CommandHandler("browser", handle_browser_command))
app.add_handler(CommandHandler("standup", standup_cmd))
app.add_handler(CommandHandler("review", review_cmd))

# Media handler — must be BEFORE the text catch-all
app.add_handler(MessageHandler(
    filters.VOICE | filters.VIDEO | filters.PHOTO
    | filters.AUDIO | filters.Document.ALL | filters.VIDEO_NOTE,
    handle_media_message,
))

# Catch-all: natural language routing — must be AFTER all CommandHandlers
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_message))

schedule_morning_briefing(app)

# Start ambient reality refresh — 30-min background loop
try:
    from eos_ai.orchestrator import start_ambient_refresh_loop
    from eos_ai.context import load_context_from_env as _lcfe
    start_ambient_refresh_loop(_lcfe())
except Exception as _amb_err:
    print(f'[Telegram] Ambient refresh start failed: {_amb_err}')

app.run_polling()
