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

    return (
        "OS Morning Briefing\n\n"
        "Pipeline:\n"
        f"  New:        {counts['New']} leads\n"
        f"  Contacted:  {counts['Contacted']} leads\n"
        f"  Replied:    {counts['Replied']} leads\n"
        f"  Booked:     {counts['Booked']} calls\n\n"
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
        time=datetime.time(hour=7, minute=0),
        chat_id=CHAT_ID,
        name="morning_briefing",
    )
    app.job_queue.run_daily(
        scheduled_eod_report,
        time=datetime.time(hour=20, minute=0),
        chat_id=CHAT_ID,
        name="eod_report",
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


async def costs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current cost breakdown."""
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

schedule_morning_briefing(app)

app.run_polling()
