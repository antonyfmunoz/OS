import os
import sys
import json
import datetime
import glob
import requests
from dotenv import load_dotenv

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(VAULT, "13_Scripts", ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
LEADS_DIR = os.path.join(VAULT, "03_CRM", "Leads")

timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
print(f"OS Overnight Scrape — {timestamp}")

import subprocess

print("\n[1/2] Running Apify scraper...")
subprocess.run(
    [sys.executable, os.path.join(VAULT, "13_Scripts/apify_scraper.py")],
    cwd=VAULT
)

print("\n[2/2] Running ICP scorer...")
subprocess.run(
    [sys.executable, os.path.join(VAULT, "13_Scripts/icp_scorer.py")],
    cwd=VAULT
)

# Count leads created today
today = datetime.date.today()
lead_files = glob.glob(os.path.join(LEADS_DIR, "lead_*.md"))
new_today = sum(
    1 for f in lead_files
    if datetime.date.fromtimestamp(os.path.getctime(f)) == today
)

# Build LEARNING block from hashtag performance
learning_block = ""
hashtag_config_path = os.path.join(VAULT, "13_Scripts/hashtag_config.json")
if os.path.exists(hashtag_config_path):
    try:
        with open(hashtag_config_path, encoding="utf-8") as f:
            hconfig = json.load(f)
        perf = hconfig.get("performance", {})
        sources_with_data = [(src, d) for src, d in perf.items() if d.get("runs", 0) > 0]
        if sources_with_data:
            sources_with_data.sort(key=lambda x: -x[1].get("avg_qualified_rate", 0))
            best_src, best_d = sources_with_data[0]
            worst_src, worst_d = sources_with_data[-1]
            best_rate = round(best_d.get("avg_qualified_rate", 0) * 100, 1)
            worst_rate = round(worst_d.get("avg_qualified_rate", 0) * 100, 1)
            blacklist = hconfig.get("blacklist", [])
            blacklisted = [s for s, _ in sources_with_data
                           if s.lstrip("#").lstrip("@") in blacklist]
            bl_msg = f"  Auto-blacklisted: {', '.join(blacklisted)}" if blacklisted else "  No blacklists this run"
            group_a = hconfig.get("groups", {}).get("A", [])
            promoted = [s for s, d in sources_with_data
                        if s.lstrip("#") in group_a and d.get("avg_qualified_rate", 0) > 0.05]
            pr_msg = f"  Auto-promoted: {', '.join(promoted)}" if promoted else "  No promotions this run"
            learning_block = (
                f"\nLEARNING\n"
                f"  Best source:  {best_src} ({best_rate}% qualified)\n"
                f"  Worst source: {worst_src} ({worst_rate}% qualified)\n"
                f"{bl_msg}\n"
                f"{pr_msg}"
            )
    except Exception:
        pass

message = (
    f"Overnight scrape complete.\n\n"
    f"New leads qualified: {new_today}\n"
    f"Ready in CRM for morning outreach.\n\n"
    f"Send /briefing for your full report."
    f"{learning_block}"
)

if TOKEN and CHAT_ID:
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
    except Exception as e:
        print(f"Telegram notification failed: {e}")

print(f"\nDone. {new_today} leads ready.")
