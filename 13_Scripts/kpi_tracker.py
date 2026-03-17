import os
import sys
import json
import glob
import datetime
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cost_tracker

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE_FILE = os.path.join(VAULT, "03_CRM/Pipeline.md")
CONVERSATIONS_DIR = os.path.join(VAULT, "03_CRM/Conversations")
DAILY_LOG = os.path.join(VAULT, "13_Scripts/daily_log.json")
SIGNALS_DIR = os.path.join(VAULT, "01_Inbox/raw_signals")

PIPELINE_STAGES = ["New", "Contacted", "Replied", "Qualifying", "Booked", "Won", "Lost"]


def get_pipeline_counts():
    """Read Pipeline.md and return stage counts dict."""
    counts = {s: 0 for s in PIPELINE_STAGES}
    if not os.path.exists(PIPELINE_FILE):
        return counts

    current_stage = None
    with open(PIPELINE_FILE, encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("## "):
                current_stage = stripped[3:].strip()
            elif stripped.startswith("- [ ]") and current_stage in counts:
                counts[current_stage] += 1

    return counts


def get_scraper_stats():
    """Find most recent scrape_summary_*.json and return stats dict."""
    zero = {"comments_scanned": 0, "bot_filtered": 0, "qualified": 0, "priority_signals": 0}

    pattern = os.path.join(SIGNALS_DIR, "scrape_summary_*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        return zero

    try:
        with open(files[0], encoding="utf-8") as f:
            data = json.load(f)
        return {
            "comments_scanned": data.get("scanned", 0),
            "bot_filtered": data.get("bot_filtered", 0) + data.get("spam_filtered", 0),
            "qualified": data.get("priority_saved", 0) + data.get("regular_saved", 0),
            "priority_signals": data.get("priority_saved", 0),
        }
    except Exception:
        return zero


def get_daily_log():
    """Read daily_log.json and return dms_sent if date is today, else 0."""
    today = datetime.date.today().isoformat()
    if not os.path.exists(DAILY_LOG):
        return {"dms_sent": 0}
    try:
        with open(DAILY_LOG, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("date") == today:
            return {"dms_sent": data.get("dms_sent", 0)}
    except Exception:
        pass
    return {"dms_sent": 0}


def get_conversation_stats():
    """Count .md files in Conversations/ modified today."""
    today = datetime.date.today()
    active_today = 0
    if not os.path.exists(CONVERSATIONS_DIR):
        return {"active_today": 0}
    for filepath in glob.glob(os.path.join(CONVERSATIONS_DIR, "*.md")):
        mtime = datetime.date.fromtimestamp(os.path.getmtime(filepath))
        if mtime == today:
            active_today += 1
    return {"active_today": active_today}


LEADS_DIR = os.path.join(VAULT, "03_CRM/Leads")
KPI_HISTORY = os.path.join(VAULT, "13_Scripts/kpi_history.json")
REPLIED_STATUSES = {"replied", "qualifying", "booked", "won"}


def _parse_lead_frontmatter(filepath):
    """Return frontmatter dict from a lead .md file."""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return {}
        end = content.find("---", 3)
        if end == -1:
            return {}
        fm = {}
        for line in content[3:end].strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"')
        return fm
    except Exception:
        return {}


def get_opener_stats():
    """Scan lead files and return openers sorted by reply rate descending."""
    stats = {}  # opener_preview -> {"sent": 0, "replied": 0}
    for filepath in glob.glob(os.path.join(LEADS_DIR, "lead_*.md")):
        fm = _parse_lead_frontmatter(filepath)
        opener = fm.get("opener_sent", "").strip()
        if not opener:
            continue
        status = fm.get("status", "new").lower()
        if opener not in stats:
            stats[opener] = {"sent": 0, "replied": 0}
        stats[opener]["sent"] += 1
        if status in REPLIED_STATUSES:
            stats[opener]["replied"] += 1

    results = []
    for opener, data in stats.items():
        rate = round(data["replied"] / data["sent"] * 100) if data["sent"] > 0 else 0
        results.append({"opener": opener, "sent": data["sent"],
                        "replied": data["replied"], "reply_rate": rate})
    results.sort(key=lambda x: (-x["reply_rate"], -x["sent"]))
    return results


def get_hashtag_stats():
    """Scan lead files and return sources sorted by reply rate descending."""
    stats = {}  # source -> {"sent": 0, "replied": 0}
    for filepath in glob.glob(os.path.join(LEADS_DIR, "lead_*.md")):
        fm = _parse_lead_frontmatter(filepath)
        source = fm.get("source", "").strip()
        if not source:
            continue
        status = fm.get("status", "new").lower()
        if source not in stats:
            stats[source] = {"sent": 0, "replied": 0}
        stats[source]["sent"] += 1
        if status in REPLIED_STATUSES:
            stats[source]["replied"] += 1

    results = []
    for source, data in stats.items():
        rate = round(data["replied"] / data["sent"] * 100) if data["sent"] > 0 else 0
        results.append({"source": source, "sent": data["sent"],
                        "replied": data["replied"], "reply_rate": rate})
    results.sort(key=lambda x: (-x["reply_rate"], -x["sent"]))
    return results


def append_kpi_history(dms_sent, replied_count):
    """Append today's reply rate to kpi_history.json."""
    today = datetime.date.today().isoformat()
    rate = round(replied_count / dms_sent * 100) if dms_sent > 0 else 0
    history = []
    if os.path.exists(KPI_HISTORY):
        try:
            with open(KPI_HISTORY, encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []
    # Update or append today's entry
    for entry in history:
        if entry.get("date") == today:
            entry["reply_rate"] = rate
            entry["dms_sent"] = dms_sent
            break
    else:
        history.append({"date": today, "reply_rate": rate, "dms_sent": dms_sent})
    # Keep last 90 days
    history = history[-90:]
    with open(KPI_HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def get_reply_rate_trend(days=7):
    """Return list of reply rates for the last N days (oldest first). Empty list if no data."""
    if not os.path.exists(KPI_HISTORY):
        return []
    try:
        with open(KPI_HISTORY, encoding="utf-8") as f:
            history = json.load(f)
        return [e["reply_rate"] for e in history[-days:]]
    except Exception:
        return []


def build_eod_report(pipeline_counts, scraper_stats, conversation_stats, daily_log):
    """Build the EOD report string."""
    date = datetime.date.today().strftime("%Y-%m-%d")
    new_count = pipeline_counts.get("New", 0)
    contacted_count = pipeline_counts.get("Contacted", 0)
    replied_count = pipeline_counts.get("Replied", 0)

    comments_scanned = scraper_stats.get("comments_scanned", 0)
    bot_filtered = scraper_stats.get("bot_filtered", 0)
    qualified = scraper_stats.get("qualified", 0)
    priority_signals = scraper_stats.get("priority_signals", 0)

    dms_sent = daily_log.get("dms_sent", 0)
    active_today = conversation_stats.get("active_today", 0)

    reply_rate = round(replied_count / dms_sent * 100) if dms_sent > 0 else 0

    if dms_sent == 0:
        performance_line = "Get your DMs out."
    elif dms_sent < 30:
        performance_line = "Halfway there — push through."
    elif dms_sent < 60:
        performance_line = f"Close — {60 - dms_sent} more to go."
    else:
        performance_line = "Full send. Good work."

    # Opener stats
    opener_stats = get_opener_stats()
    opener_block = ""
    if opener_stats:
        lines = []
        for i, row in enumerate(opener_stats[:3], 1):
            lines.append(f"  {i}. '{row['opener'][:40]}' — {row['reply_rate']}% ({row['sent']} sent)")
        opener_block = "TOP OPENERS\n" + "\n".join(lines) + "\n\n"

    # Hashtag / source stats (only if 5+ total leads)
    hashtag_stats = get_hashtag_stats()
    total_leads = sum(r["sent"] for r in hashtag_stats)
    source_block = ""
    if total_leads >= 5 and hashtag_stats:
        lines = []
        for i, row in enumerate(hashtag_stats[:3], 1):
            lines.append(f"  {i}. {row['source']} — {row['reply_rate']}% reply rate ({row['sent']} leads)")
        source_block = "TOP SOURCES\n" + "\n".join(lines) + "\n\n"

    cost_report = cost_tracker.format_cost_report()
    cost_summary = cost_tracker.get_cost_summary()
    today_scraper = cost_summary["today_scraper"]
    today_copilot = cost_summary["today_copilot"]
    today_total = cost_summary["today_total"]
    month_total = cost_summary["month_total"]
    all_time = cost_summary["all_time_total"]

    append_kpi_history(dms_sent, replied_count)

    return (
        f"OS — Daily Outreach Report\n"
        f"{date}\n\n"
        f"SCRAPER\n"
        f"  Scanned:     {comments_scanned}\n"
        f"  Qualified:   {qualified} leads\n"
        f"  Priority:    {priority_signals} high intent\n"
        f"  Bots caught: {bot_filtered}\n\n"
        f"OUTREACH\n"
        f"  Leads ready: {new_count}\n"
        f"  DMs sent:    {dms_sent} / 60\n"
        f"  Replies:     {replied_count}\n"
        f"  Reply rate:  {reply_rate}%\n"
        f"  Active DMs:  {active_today}\n\n"
        f"PIPELINE\n"
        f"  New:         {new_count}\n"
        f"  Contacted:   {contacted_count}\n"
        f"  Replied:     {replied_count}\n\n"
        f"{opener_block}"
        f"{source_block}"
        f"COSTS\n"
        f"  Scraper:     ${today_scraper:.4f}\n"
        f"  Co-pilot:    ${today_copilot:.4f}\n"
        f"  Today total: ${today_total:.4f}\n"
        f"  This month:  ${month_total:.2f}\n"
        f"  All time:    ${all_time:.2f}\n\n"
        f"{performance_line}\n\n"
        f"Outreach earns everything."
    )


def send_telegram(text):
    """Send a message to Telegram via the Bot API."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set in .env")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)


def main():
    pipeline_counts = get_pipeline_counts()
    scraper_stats = get_scraper_stats()
    conversation_stats = get_conversation_stats()
    daily_log = get_daily_log()

    report = build_eod_report(pipeline_counts, scraper_stats, conversation_stats, daily_log)

    send_telegram(report)
    print(report)
    print("EOD report sent.")


if __name__ == "__main__":
    main()
