import os
import sys
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

message = (
    f"Overnight scrape complete.\n\n"
    f"New leads qualified: {new_today}\n"
    f"Ready in CRM for morning outreach.\n\n"
    f"Send /briefing for your full report."
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
