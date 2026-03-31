import subprocess
import sys
import json
import glob
import time
import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_LEADS = 60
MAX_ATTEMPTS = 5
COST_TIERS = [5.00, 10.00, 15.00, 20.00]


def send_telegram(text):
    if not TOKEN or not CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text},
            timeout=10
        )
    except Exception:
        pass


def count_new_leads_today():
    today = datetime.date.today().isoformat()
    leads_dir = os.path.join(VAULT, "03_CRM/Leads")
    count = 0
    for f in glob.glob(os.path.join(leads_dir, "lead_*.md")):
        if today in os.path.basename(f):
            count += 1
    return count


def get_today_cost():
    try:
        cost_log = os.path.join(VAULT, "13_Scripts/cost_log.json")
        if not os.path.exists(cost_log):
            return 0.0
        with open(cost_log) as f:
            data = json.load(f)
        today = datetime.date.today().isoformat()
        return data.get("daily", {}).get(today, {}).get("total_day", 0.0)
    except Exception:
        return 0.0


def force_group_a():
    config_path = os.path.join(VAULT, "13_Scripts/hashtag_config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
        config["current_group"] = "A"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print("Switched to Group A for retry.")
    except Exception as e:
        print(f"Could not switch group: {e}")


def get_scrape_stats():
    today = datetime.date.today().isoformat()
    summary_path = os.path.join(
        VAULT, f"01_Inbox/raw_signals/scrape_summary_{today}.json")
    if not os.path.exists(summary_path):
        return {}
    with open(summary_path) as f:
        return json.load(f)


def get_hashtag_learning():
    config_path = os.path.join(VAULT, "13_Scripts/hashtag_config.json")
    if not os.path.exists(config_path):
        return "No hashtag data yet."
    with open(config_path) as f:
        config = json.load(f)
    perf = config.get("performance", {})
    if not perf:
        return "No performance data yet."
    sorted_h = sorted(
        perf.items(),
        key=lambda x: x[1].get("avg_qualified_rate", 0),
        reverse=True
    )
    lines = []
    if sorted_h:
        best = sorted_h[0]
        worst = sorted_h[-1]
        lines.append(
            f"Best: {best[0]} "
            f"({best[1].get('avg_qualified_rate', 0)*100:.1f}%)")
        lines.append(
            f"Worst: {worst[0]} "
            f"({worst[1].get('avg_qualified_rate', 0)*100:.1f}%)")
    return "\n".join(lines)


def check_cost_approval(current_cost, leads_so_far, approved_limit):
    tier_index = COST_TIERS.index(approved_limit)
    if tier_index + 1 >= len(COST_TIERS):
        return False, approved_limit
    next_tier = COST_TIERS[tier_index + 1]
    send_telegram(
        f"COST CAP HIT\n\n"
        f"Spent tonight: ${current_cost:.2f}\n"
        f"Leads collected: {leads_so_far}/60\n\n"
        f"Approve ${next_tier:.0f} limit to continue?\n"
        f"Reply /approve to continue\n"
        f"Reply /stop to stop now\n\n"
        f"Auto-stops in 5 minutes if no response."
    )
    approval_file = os.path.join(VAULT, "13_Scripts/approval_response.txt")
    if os.path.exists(approval_file):
        os.remove(approval_file)
    for _ in range(30):
        time.sleep(10)
        if os.path.exists(approval_file):
            with open(approval_file) as f:
                response = f.read().strip().lower()
            os.remove(approval_file)
            if response == "approve":
                return True, next_tier
            else:
                return False, approved_limit
    return False, approved_limit


def run_scraper(ignore_cache=False):
    env = os.environ.copy()
    if ignore_cache:
        env["SCRAPER_IGNORE_CACHE"] = "1"
    result = subprocess.run(
        [sys.executable, os.path.join(VAULT, "13_Scripts/apify_scraper.py")],
        cwd=VAULT, capture_output=False, env=env
    )
    return result.returncode == 0


def run_scorer():
    result = subprocess.run(
        [sys.executable, os.path.join(VAULT, "13_Scripts/icp_scorer.py")],
        cwd=VAULT, capture_output=False
    )
    return result.returncode == 0


def main():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"OS Overnight Scrape — {timestamp}")
    print(f"Target: {TARGET_LEADS} leads\n")

    existing = count_new_leads_today()
    if existing >= TARGET_LEADS:
        print(f"{existing} leads already collected. Done.")
        return

    approved_limit = COST_TIERS[0]
    total_leads = existing
    attempt = 0

    while total_leads < TARGET_LEADS and attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"\nAttempt {attempt}/{MAX_ATTEMPTS}")
        print(f"Leads so far: {total_leads}/{TARGET_LEADS}")

        tonight_cost = get_today_cost()
        if tonight_cost >= approved_limit:
            approved, approved_limit = check_cost_approval(
                tonight_cost, total_leads, approved_limit)
            if not approved:
                print("Cost not approved. Stopping.")
                break

        print("Running Apify scraper...")
        run_scraper(ignore_cache=(attempt > 1))

        print("Running ICP scorer...")
        run_scorer()

        # Notify gateway that a scoring batch completed
        batch_size = count_new_leads_today() - total_leads
        try:
            sys.path.insert(0, VAULT)
            from eos_ai.gateway import EOSGateway
            EOSGateway().handle({
                "type":       "event",
                "event_type": "signal_captured",
                "payload": {
                    "batch_size": max(batch_size, 0),
                    "attempt":    attempt,
                    "venture_id": "lyfe_institute",
                },
            })
        except Exception as _gw_err:
            print(f"[Gateway] signal_captured event failed: {_gw_err}")

        total_leads = count_new_leads_today()
        print(f"Total leads: {total_leads}/{TARGET_LEADS}")

        if total_leads >= TARGET_LEADS:
            break

        if attempt < MAX_ATTEMPTS and total_leads < TARGET_LEADS:
            remaining = TARGET_LEADS - total_leads
            print(f"Need {remaining} more leads.")
            print("Retrying with competitor accounts...")
            if total_leads == 0:
                force_group_a()

    stats = get_scrape_stats()
    learning = get_hashtag_learning()
    tonight_cost = get_today_cost()

    if total_leads >= TARGET_LEADS:
        header = f"Leads Ready — {total_leads}/60"
        status = "Open Pipeline.md — leads are ready.\nSend /dms_sent when outreach is complete."
    else:
        header = f"Partial Scrape — {total_leads}/60 leads"
        status = "System will try again tomorrow.\nUse /hashtags to review performance."

    message = (
        f"OS — {header}\n\n"
        f"Attempts: {attempt}\n\n"
        f"PIPELINE\n"
        f"  New leads: {total_leads}\n\n"
        f"SCRAPER\n"
        f"  Scanned: {stats.get('scanned', 0)}\n"
        f"  Qualified: {stats.get('priority_saved', 0) + stats.get('regular_saved', 0)}\n"
        f"  Bots caught: {stats.get('bot_filtered', 0)}\n\n"
        f"LEARNING\n"
        f"  {learning}\n\n"
        f"COSTS\n"
        f"  Tonight: ${tonight_cost:.4f}\n\n"
        f"{status}"
    )
    send_telegram(message)
    print(f"\nDone. {total_leads} leads ready.")


if __name__ == "__main__":
    main()
