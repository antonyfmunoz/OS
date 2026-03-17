import os
import sys
import time
import subprocess
from dotenv import load_dotenv

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FILES = [
    "13_Scripts/.env",
    "13_Scripts/apify_scraper.py",
    "13_Scripts/icp_scorer.py",
    "13_Scripts/dm_monitor.py",
    "13_Scripts/telegram_control.py",
]

REQUIRED_ENV = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "APIFY_API_TOKEN",
]

PROCESSES = {
    "Telegram bot": ["python", "13_Scripts/telegram_control.py"],
    "DM monitor":   ["python", "13_Scripts/dm_monitor.py"],
}

BANNER = """
+===================================+
|           OS - STARTING           |
+===================================+
"""

LIVE_MSG = """
System is live.

Telegram commands available:
/briefing  — morning leads report
/research  — run signal intelligence
/report    — generate market report
/content   — generate content ideas
/outreach  — generate outreach messages
/status    — system status

Press Ctrl+C to stop all processes.
"""


def check_files():
    missing = False
    for rel in REQUIRED_FILES:
        path = os.path.join(VAULT, rel)
        if not os.path.exists(path):
            print(f"MISSING: {rel}")
            missing = True
    if missing:
        sys.exit(1)


def check_env():
    load_dotenv(os.path.join(VAULT, "13_Scripts", ".env"))
    missing = False
    for var in REQUIRED_ENV:
        if not os.getenv(var):
            print(f"ENV MISSING: {var}")
            missing = True
    if missing:
        sys.exit(1)


def start_process(name, cmd):
    return subprocess.Popen(cmd, cwd=VAULT)


def main():
    print(BANNER)

    check_files()
    check_env()

    procs = {}
    for name, cmd in PROCESSES.items():
        procs[name] = start_process(name, cmd)
        label = "Telegram bot" if "telegram" in cmd[-1] else "DM monitor"
        print(f"[OK] {label} started")

    print(LIVE_MSG)

    try:
        while True:
            for name, cmd in PROCESSES.items():
                proc = procs[name]
                if proc.poll() is not None:
                    print(f"[!!] {name} crashed -- restarting in 10s...")
                    time.sleep(10)
                    procs[name] = start_process(name, cmd)
                    print(f"[OK] {name} restarted")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for name, proc in procs.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("OS shut down.")


if __name__ == "__main__":
    main()
