import subprocess
import os
import sys
import json
import glob
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kpi_tracker
import cost_tracker

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # target chat for scheduled briefing
VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_FILE = os.path.join(VAULT, "03_CRM/Pipeline.md")

PIPELINE_STAGES = ["New", "Contacted", "Replied", "Qualifying", "Booked", "Won", "Lost"]


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
        "13_Scripts/revenue_log.json")
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


async def run_command(command, update: Update):
    result = subprocess.run(
        ["C:/Program Files/Git/bin/bash.exe", "-c", command],
        capture_output=True, text=True, cwd=VAULT
    )
    output = result.stdout.strip() or result.stderr.strip() or "Done. No output returned."
    if len(output) > 4096:
        output = output[:4090] + "\n..."
    await update.message.reply_text(output)


async def research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Signal research started...")
    await run_command("./13_Scripts/os.sh research", update)


async def market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Market report generating...")
    await run_command("./13_Scripts/os.sh report", update)


async def content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Content engine running...")
    await run_command("./13_Scripts/os.sh content", update)


async def outreach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Outreach messages generating...")
    await run_command("./13_Scripts/os.sh outreach", update)


async def leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Lead signals generating...")
    await run_command("./13_Scripts/lead_qualifier.sh", update)


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
    history_path = os.path.join(VAULT, "13_Scripts/kpi_history.json")
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
        "13_Scripts/revenue_log.json")
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
    config_path = os.path.join(VAULT, "13_Scripts/hashtag_config.json")
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
    config_path = os.path.join(VAULT, "13_Scripts/hashtag_config.json")
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
        "13_Scripts/calls_log.json")
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
        "13_Scripts/revenue_log.json")

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
        "13_Scripts/revenue_log.json")
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
    approval_file = os.path.join(VAULT, "13_Scripts/approval_response.txt")
    with open(approval_file, "w") as f:
        f.write("approve")
    await update.message.reply_text("Approved. Scraper continuing to next tier.")


async def stop_scraper(update: Update, context: ContextTypes.DEFAULT_TYPE):
    approval_file = os.path.join(VAULT, "13_Scripts/approval_response.txt")
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


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("research", research))
app.add_handler(CommandHandler("market", market))
app.add_handler(CommandHandler("content", content))
app.add_handler(CommandHandler("outreach", outreach))
app.add_handler(CommandHandler("leads", leads))
app.add_handler(CommandHandler("briefing", send_morning_briefing))
app.add_handler(CommandHandler("sent", sent))
app.add_handler(CommandHandler("report", report))
app.add_handler(CommandHandler("costs", costs))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("hashtags", hashtags))
app.add_handler(CommandHandler("blacklist", blacklist_tag))
app.add_handler(CommandHandler("addhashtag", add_hashtag))
app.add_handler(CommandHandler("approve", approve_cost))
app.add_handler(CommandHandler("stop", stop_scraper))
app.add_handler(CommandHandler("closed", closed))
app.add_handler(CommandHandler("revenue", revenue))
app.add_handler(CommandHandler("showed", showed))
app.add_handler(CommandHandler("noshow", noshow))

schedule_morning_briefing(app)

app.run_polling()
