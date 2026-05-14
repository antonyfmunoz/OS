import os
import sys
import json
import glob
import time
import random
import datetime
import base64
import uuid
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cost_tracker

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from runtime.agent_runtime import AgentRuntime
from runtime.context import load_context_from_env
from runtime.memory import AgentMemory
from runtime.error_handler import ErrorHandler

_ctx = load_context_from_env()
_runtime = AgentRuntime(_ctx)
_mem = AgentMemory()
_err = ErrorHandler("dm_monitor", _ctx)

try:
    from google import genai

    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# GEMINI_API_KEY is optional — used as Vision fallback for DOM extraction failures
# Get from: console.cloud.google.com → APIs → Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if _GENAI_AVAILABLE and GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(VAULT, "services", "instagram_session")
CONVERSATIONS_DIR = os.path.join(VAULT, "03_CRM", "Conversations")
SCREENSHOTS_DIR = os.path.join(CONVERSATIONS_DIR, "screenshots")

# TASK 5 — per-run state to skip threads with no new activity
# {username: {"last_message": "...", "last_message_count": 3}}
conversation_states = {}

SALES_SYSTEM_PROMPT = """You are a sales conversation assistant for Initiate Arena — a 90-day discipline and execution program for ambitious men aged 18-25.

SALES PLAYBOOK:
- Never pitch immediately — diagnose first
- Goal: book a discovery call
- Conversation stages: Cold → Engaged → Diagnosing → Qualifying → Booked
- Only invite to a call when ALL THREE are present:
  1. Frustration (they feel stuck, wasting time, not executing)
  2. Self-awareness (they know they're the problem, not external factors)
  3. Ownership (they want to change and take responsibility)

RULES:
- Ask one question at a time
- Go deep on their pain before any mention of a solution
- Never sound salesy — sound like a person who genuinely cares
- Short replies only: 1-3 sentences max
- Mirror their language and energy

Analyze the conversation, detect the current stage, and suggest the single best next reply."""


def send_telegram(text):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured — skipping notification.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        print(f"Telegram send failed: {e}")


def load_workflow_prompt(filename):
    path = os.path.join(
        VAULT, "05_Workflows", "Sales", "conversation_assistant", filename
    )
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def get_vault_path():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def move_card_to_stage(username, from_stage, to_stage):
    """Find the kanban card for username in from_stage and move it to to_stage.
    Returns True if moved, False if not found or already in another stage."""
    pipeline_file = os.path.join(get_vault_path(), "03_CRM/Pipeline.md")
    if not os.path.exists(pipeline_file):
        return False

    with open(pipeline_file, encoding="utf-8") as f:
        lines = f.read().splitlines()

    # Find card in from_stage section
    current_section = None
    card_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
        elif current_section == from_stage:
            if (
                stripped.startswith(("- [ ]", "- [x]"))
                and username.lower() in stripped.lower()
            ):
                card_idx = i
                break

    if card_idx is None:
        # Check if card exists in any other section (already moved — skip)
        for line in lines:
            stripped = line.strip()
            if (
                stripped.startswith(("- [ ]", "- [x]"))
                and username.lower() in stripped.lower()
            ):
                return False  # found elsewhere
        return False  # not found at all

    card_line = lines[card_idx]
    lines.pop(card_idx)

    # Find insertion point: right after "false" under **Complete** in to_stage section
    current_section = None
    insert_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
        elif current_section == to_stage and stripped == "false":
            insert_idx = i + 1
            break

    if insert_idx is None:
        # Fallback: insert right after the ## to_stage header line
        for i, line in enumerate(lines):
            if line.strip() == f"## {to_stage}":
                insert_idx = i + 1
                break

    if insert_idx is None:
        return False

    lines.insert(insert_idx, card_line)

    with open(pipeline_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return True


def update_lead_stage(username, new_stage, conversation_stage=None):
    """Update kanban_stage, status, conversation_stage, and last_stage_update in the lead's frontmatter."""
    pattern = os.path.join(get_vault_path(), f"03_CRM/Leads/lead_{username}_*.md")
    lead_files = glob.glob(pattern)
    if not lead_files:
        return
    filepath = sorted(lead_files)[-1]  # most recent
    with open(filepath, encoding="utf-8") as f:
        lines = f.read().splitlines()

    today = datetime.date.today().isoformat()
    fields_written = {
        "kanban_stage": False,
        "status": False,
        "conversation_stage": False,
        "last_stage_update": False,
    }

    for i, line in enumerate(lines):
        if line.startswith("kanban_stage:"):
            lines[i] = f"kanban_stage: {new_stage}"
            fields_written["kanban_stage"] = True
        elif line.startswith("status:"):
            lines[i] = f"status: {new_stage.lower()}"
            fields_written["status"] = True
        elif line.startswith("conversation_stage:"):
            if conversation_stage:
                lines[i] = f"conversation_stage: {conversation_stage}"
            fields_written["conversation_stage"] = True
        elif line.startswith("last_stage_update:"):
            lines[i] = f"last_stage_update: {today}"
            fields_written["last_stage_update"] = True

    # Append any fields that weren't already in the frontmatter
    # Find the closing --- of the frontmatter block
    fm_end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            fm_end = i
            break

    if fm_end is not None:
        inserts = []
        if not fields_written["conversation_stage"] and conversation_stage:
            inserts.append(f"conversation_stage: {conversation_stage}")
        if not fields_written["last_stage_update"]:
            inserts.append(f"last_stage_update: {today}")
        for field in reversed(inserts):
            lines.insert(fm_end, field)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def parse_frontmatter_dm(content):
    """Parse YAML frontmatter from a lead file. Returns (meta dict, body str)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    meta = {}
    for line in content[3:end].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"')
    return meta, content[end + 3 :].strip()


def update_source_booked(username):
    vault = get_vault_path()
    lead_files = glob.glob(os.path.join(vault, f"03_CRM/Leads/lead_{username}_*.md"))
    if not lead_files:
        return
    with open(sorted(lead_files)[-1], encoding="utf-8") as f:
        content = f.read()
    meta, _ = parse_frontmatter_dm(content)
    source = meta.get("source", "")
    if not source:
        return
    config_path = os.path.join(vault, "services/hashtag_config.json")
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        perf = config.get("performance", {})
        if source in perf:
            perf[source]["booked_count"] = perf[source].get("booked_count", 0) + 1
            total = perf[source].get("total_qualified", 1)
            perf[source]["booking_rate"] = round(
                perf[source]["booked_count"] / total, 4
            )
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"  [BOOKING TRACK] Failed: {e}")


def update_source_reply(username):
    """Update source hashtag reply count and opener reply count when a lead replies."""
    vault = get_vault_path()

    pattern = os.path.join(vault, f"03_CRM/Leads/lead_{username}_*.md")
    lead_files = glob.glob(pattern)
    if not lead_files:
        return
    filepath = sorted(lead_files)[-1]

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            return
        end = content.find("---", 3)
        if end == -1:
            return
        fm = {}
        for line in content[3:end].strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"')
    except Exception:
        return

    source = fm.get("source", "").strip()
    opener_sent = fm.get("opener_sent", "").strip()

    # Update hashtag_config.json reply count
    if source:
        config_path = os.path.join(vault, "services/hashtag_config.json")
        try:
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
            perf = config.get("performance", {})
            if source in perf:
                perf[source].setdefault("reply_count", 0)
                perf[source]["reply_count"] += 1
                total_qualified = perf[source].get("total_qualified", 0)
                reply_count = perf[source]["reply_count"]
                if total_qualified > 0:
                    perf[source]["reply_rate"] = round(reply_count / total_qualified, 4)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"  [REPLY TRACK] Source update failed: {e}")

    # Update opener_stats.json reply count
    if opener_sent:
        opener_stats_path = os.path.join(vault, "services/opener_stats.json")
        try:
            if os.path.exists(opener_stats_path):
                with open(opener_stats_path, encoding="utf-8") as f:
                    stats = json.load(f)
            else:
                stats = {"openers": {}}
            openers = stats.setdefault("openers", {})
            openers.setdefault(
                opener_sent, {"sent": 0, "replies": 0, "reply_rate": 0.0}
            )
            openers[opener_sent]["replies"] += 1
            sent = openers[opener_sent]["sent"]
            replies = openers[opener_sent]["replies"]
            if sent > 0:
                openers[opener_sent]["reply_rate"] = round(replies / sent, 4)
            with open(opener_stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"  [REPLY TRACK] Opener update failed: {e}")


def _log_rlhf_outcome(username, outcome_type, score, notes=None):
    """
    Look up interaction_id for username in memory.db and log an outcome.
    If no interaction found, logs to orphaned_replies for manual reconciliation.
    Silent on all errors — never crashes the monitor.
    """
    try:
        row = _mem.get_interaction_for_lead(username, venture_id="lyfe_institute")
        if row:
            _mem.log_outcome(row["id"], outcome_type, score=score, notes=notes)
            print(
                f"  [RLHF] @{username} → {outcome_type} (score={score}) — interaction_id={row['id']}"
            )
        else:
            _mem.log_orphaned_reply(
                username,
                outcome_type=outcome_type,
                score=score,
                notes=notes or "no matching interaction in memory.db",
            )
            print(
                f"  [RLHF] @{username} → orphaned {outcome_type} (no interaction found)"
            )
    except Exception as e:
        print(f"  [RLHF] outcome logging failed for @{username}: {e}")


def _advance_pipeline(username, stage):
    """Move the pipeline card based on conversation stage.
    Returns (pipeline_status_str, ready_alert_str|None)."""
    pipeline_status = None
    ready_alert = None

    if stage in ("Engaged", "Diagnosing", "Qualifying", "Ready", "Booked"):
        moved = move_card_to_stage(username, "Contacted", "Replied")
        if moved:
            update_lead_stage(username, "Replied", conversation_stage=stage)
            pipeline_status = "Contacted → Replied"
            update_source_reply(username)
            _log_rlhf_outcome(username, "reply", 1.0)
            print(f"  [PIPELINE] @{username} Contacted → Replied")
        else:
            update_lead_stage(username, "Replied", conversation_stage=stage)
            print(f"  [PIPELINE] @{username} not in Contacted — skipping Replied move")

    if stage in ("Qualifying", "Ready", "Booked"):
        moved = move_card_to_stage(username, "Replied", "Qualifying")
        if not moved:
            moved = move_card_to_stage(username, "Contacted", "Qualifying")
        if moved:
            update_lead_stage(username, "Qualifying", conversation_stage=stage)
            pipeline_status = (
                (pipeline_status + " → Qualifying")
                if pipeline_status
                else "→ Qualifying"
            )
            print(f"  [PIPELINE] @{username} → Qualifying")

    if stage == "Booked":
        moved = move_card_to_stage(username, "Qualifying", "Booked")
        if moved:
            update_lead_stage(username, "Booked", conversation_stage=stage)
            pipeline_status = (
                (pipeline_status + " → Booked") if pipeline_status else "→ Booked"
            )
            update_source_booked(username)
            _log_rlhf_outcome(username, "booked", 1.0)
            print(f"  [PIPELINE] @{username} → Booked")

    if stage == "Ready":
        ready_alert = (
            f"\U0001f525 CALL INVITE READY\n\n"
            f"@{username} is ready for a call invite.\n\n"
            f"Their signals:\n"
            f"- Pain confirmed\n"
            f"- Self-awareness present\n"
            f"- Ownership language detected\n\n"
            f"Send this:\n"
            f'"Want to see if it\u2019s a fit? '
            f'I can jump on a quick call this week."'
        )

    if not pipeline_status:
        # Still update conversation_stage even when no card move
        update_lead_stage(username, "Contacted", conversation_stage=stage)
        pipeline_status = f"Stage: {stage} (no move)"

    return pipeline_status, ready_alert


def extract_messages_from_screenshot(screenshot_path):
    """Use Gemini Vision to extract conversation from screenshot.
    Returns list of message dicts: [{"sender": "me"|"them", "text": "..."}]
    Falls back gracefully if Gemini unavailable."""
    if not gemini_client:
        return []
    if not os.path.exists(screenshot_path):
        return []
    try:
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        prompt = """This is a screenshot of an Instagram DM conversation.

Extract all visible messages in order.
For each message identify:
- sender: "me" if it appears on the right side (sent), "them" if on left side (received)
- text: the exact message text

Return ONLY valid JSON, no other text:
{
  "messages": [
    {"sender": "me", "text": "message text"},
    {"sender": "them", "text": "their reply"}
  ],
  "last_sender": "them",
  "message_count": 2
}

If you cannot read the messages clearly return:
{"messages": [], "last_sender": null, "message_count": 0}"""

        response = gemini_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {"mime_type": "image/png", "data": image_data},
                prompt,
            ],
        )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)
        return data.get("messages", [])

    except Exception as e:
        print(f"  [GEMINI] Vision extraction failed: {e}")
        return []


def detect_stage(conversation_text):
    text_lower = conversation_text.lower()
    if any(
        w in text_lower
        for w in ["let's hop on", "book a call", "schedule", "zoom", "calendly"]
    ):
        return "Booked"
    if any(
        w in text_lower
        for w in [
            "how long",
            "what does that cost",
            "what's included",
            "tell me more about",
        ]
    ):
        return "Qualifying"
    # Ready = ownership + urgency — all 3 call-invite signals present
    if any(
        w in text_lower
        for w in [
            "i'm ready",
            "i need to fix this",
            "ready to commit",
            "what do i need to do",
            "how do i get started",
            "i want to change",
            "i'm done wasting",
            "sign me up",
        ]
    ):
        return "Ready"
    if any(
        w in text_lower
        for w in [
            "i feel",
            "i keep",
            "i can't",
            "i never",
            "i always",
            "i'm struggling",
        ]
    ):
        return "Diagnosing"
    if any(w in text_lower for w in ["yeah", "true", "exactly", "i know", "honestly"]):
        return "Engaged"
    return "Cold"


def generate_reply(conversation_text):
    extra_context = load_workflow_prompt("2_analyze_conversation.md")
    extra_context += "\n\n" + load_workflow_prompt("3_generate_response.md")

    system = SALES_SYSTEM_PROMPT
    if extra_context.strip():
        system += f"\n\n---\nADDITIONAL CONTEXT:\n{extra_context}"

    _prompt = f"Here is the conversation so far. Suggest the best next reply (1-3 sentences max):\n\n{conversation_text}"
    try:
        from runtime.model_router import call_with_fallback
        _result = call_with_fallback(
            prompt=_prompt,
            system=system,
            task_type="fast_response",
            agent_type="sales",
        )
        if _result and _result.output:
            return _result.output.strip()
        return "What made you reach out today?"
    except Exception as e:
        print(f"[dm_monitor] model_router failed: {e}")
        return "What made you reach out today?"


def save_conversation(username, messages_text, stage, analysis):
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)
    today = datetime.date.today().isoformat()
    filepath = os.path.join(CONVERSATIONS_DIR, f"{username}.md")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            existing = f.read()
        # Update stage in frontmatter
        lines = existing.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("stage:"):
                lines[i] = f"stage: {stage}"
            if line.startswith("date:"):
                lines[i] = f"date: {today}"
        # Find the last analysis section and append after it
        updated = "\n".join(lines)
        updated = updated.rstrip()
        updated += f"\n\n---\n## Latest Analysis — {now}\n{analysis}\n"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(updated)
    else:
        content = f"""---
lead: {username}
platform: DM
date: {today}
status: Active
stage: {stage}
---

# Conversation: {username}

{messages_text}

---
## Latest Analysis — {now}
{analysis}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    return filepath


def cleanup_old_screenshots():
    screenshots_dir = os.path.join(get_vault_path(), "03_CRM/Conversations/screenshots")
    if not os.path.exists(screenshots_dir):
        return
    cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
    removed = 0
    for filepath in glob.glob(os.path.join(screenshots_dir, "*.png")):
        try:
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1
        except Exception:
            pass
    if removed > 0:
        print(f"[CLEANUP] Removed {removed} screenshots older than 30 days")


def send_telegram_alert(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10,
        )
    except Exception:
        pass


def send_discord_webhook(env_var: str, content: str) -> None:
    """Post to a Discord channel via incoming webhook URL stored in env."""
    from runtime.discord_utils import post_to_webhook

    webhook_url = os.getenv(env_var)
    if not webhook_url:
        return
    post_to_webhook(content, webhook_url=webhook_url)


def get_session_path():
    return os.path.join(get_vault_path(), "services/instagram_session.json")


def save_session(context):
    """Save full browser auth state (cookies + localStorage) via storage_state."""
    try:
        context.storage_state(path=get_session_path())
        print("[SESSION] Storage state saved.")
    except Exception as e:
        print(f"[SESSION] Could not save storage state: {e}")


def load_session_exists() -> bool:
    """Return True if a saved storage state file exists."""
    return os.path.exists(get_session_path())


def session_is_valid(page):
    try:
        page.goto(
            "https://www.instagram.com/direct/inbox/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        time.sleep(random.uniform(3, 5))
        if "login" in page.url:
            return False
        return True
    except Exception:
        return False


def _screenshot_login_state(page, label="login"):
    """Save a screenshot to logs/ for diagnosing what Instagram is showing."""
    try:
        os.makedirs(os.path.join(_REPO_ROOT, "logs"), exist_ok=True)
        path = os.path.join(_REPO_ROOT, "logs", f"instagram_{label}.png")
        page.screenshot(path=path)
        print(f"[dm_monitor] Screenshot saved: {path}")
    except Exception as _se:
        print(f"[dm_monitor] Screenshot failed: {_se}")


_CODE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "instagram_code.txt"
)


def _wait_for_telegram_code(timeout: int = 600) -> str | None:
    """
    Watch /opt/OS/services/instagram_code.txt for a 6-digit code.

    os-bot and dm_monitor share the same bot token — getUpdates is a single
    stream and os-bot consumes messages first. File-based relay sidesteps
    the race: the user (or os-bot) writes the code to the file, dm_monitor
    reads and deletes it.

    To send the code:
        echo "847291" > /opt/OS/services/instagram_code.txt
    """
    import re

    # Clean up any stale code file from a previous attempt
    try:
        os.remove(_CODE_FILE)
    except FileNotFoundError:
        pass

    print(f"[SESSION] Waiting for 6-digit code in {_CODE_FILE} (up to 10min)...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(_CODE_FILE):
            try:
                with open(_CODE_FILE) as f:
                    text = f.read().strip()
                os.remove(_CODE_FILE)
                if re.match(r"^\d{6}$", text):
                    print(f"[SESSION] Code read from file: {text}")
                    return text
                else:
                    print(f"[SESSION] File contained non-code value: {repr(text)}")
            except Exception as e:
                print(f"[SESSION] Error reading code file: {e}")
        time.sleep(3)
    return None


def _wait_for_telegram_code_UNUSED(timeout: int = 600) -> str | None:
    """Kept for reference — broken because os-bot consumes getUpdates first."""
    import re

    if not TELEGRAM_BOT_TOKEN:
        return None
    deadline = time.time() + timeout
    offset = None
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
            params={"offset": -1, "limit": 1},
            timeout=10,
        )
        if resp.ok:
            updates = resp.json().get("result", [])
            if updates:
                offset = updates[-1]["update_id"] + 1
    except Exception:
        pass

    while time.time() < deadline:
        try:
            params: dict = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params=params,
                timeout=35,
            )
            if resp.ok:
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    text = update.get("message", {}).get("text", "").strip()
                    if re.match(r"^\d{6}$", text):
                        print(f"[SESSION] Code received from Telegram: {text}")
                        return text
        except Exception as e:
            print(f"[SESSION] Telegram poll error: {e}")
            time.sleep(5)
    return None


def do_login(page, context):
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    if not username or not password:
        send_telegram_alert("INSTAGRAM LOGIN FAILED\n\nMissing credentials in .env")
        return False
    try:
        # Navigate to root — Instagram serves login form here without bot
        # challenge. Direct /accounts/login/ returns a blank page from VPS IPs.
        page.goto(
            "https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000
        )
        time.sleep(8)

        # Dismiss cookie consent if present
        try:
            for text in [
                "Allow all cookies",
                "Accept All",
                "Allow essential and optional cookies",
            ]:
                btn = page.locator(f'button:has-text("{text}")')
                if btn.is_visible(timeout=3000):
                    btn.click()
                    time.sleep(2)
                    break
        except Exception:
            pass

        print(f"[SESSION] Post-cookie URL: {page.url}")

        # Log exactly where we are before trying to fill
        print(f"[SESSION] Pre-fill URL: {page.url}")
        try:
            print(f"[SESSION] Page title: {page.title()}")
        except Exception:
            pass

        # Wait for page to fully render
        time.sleep(20)

        # Screenshot before attempting fill — captures what Instagram is showing
        _screenshot_login_state(page, "pre_fill")

        # Dump all input fields in the DOM for diagnosis
        try:
            inputs = page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).map(i => ({
                    name: i.name, type: i.type, autocomplete: i.autocomplete,
                    ariaLabel: i.getAttribute('aria-label'),
                    placeholder: i.placeholder, id: i.id
                }));
            }""")
            print(f"[SESSION] Input fields found in DOM: {inputs}")
        except Exception as _dom_err:
            print(f"[SESSION] DOM dump failed: {_dom_err}")

        # Try multiple selectors in case Instagram changed the login DOM
        # DOM confirmed: name="email", autocomplete="username webauthn", no aria-label
        _username_selectors = [
            'input[name="email"]',
            'input[autocomplete*="username"]',
            'input[name="username"]',
            'input[aria-label="Mobile number, username or email"]',
            'input[aria-label="Phone number, username, or email"]',
            'input[aria-label*="username"]',
            '#loginForm input[type="text"]',
            'form input[type="text"]',
        ]
        username_input = None
        for sel in _username_selectors:
            try:
                el = page.locator(sel)
                el.wait_for(timeout=5000)
                username_input = el
                print(f"[SESSION] Username input found via: {sel}")
                break
            except Exception as _sel_err:
                print(f"[SESSION] Selector failed '{sel}': {_sel_err}")
                continue

        if not username_input:
            _screenshot_login_state(page, "no_username_input")
            raise Exception(
                f"No username input found (URL: {page.url}) — "
                "Instagram may be showing a challenge or changed login page. "
                "See /opt/OS/logs/instagram_no_username_input.png"
            )

        # React-controlled inputs reject synthetic fill — click then type char by char
        print("[SESSION] Typing username...")
        username_input.click()
        time.sleep(0.5)
        username_input.type(username, delay=80)
        time.sleep(2)
        print("[SESSION] Typing password...")
        # DOM confirmed: password field is name="pass" not name="password"
        password_input = page.locator(
            'input[name="pass"], input[type="password"]'
        ).first
        password_input.wait_for(timeout=10000)
        password_input.click()
        time.sleep(0.5)
        password_input.type(password, delay=80)
        time.sleep(1)
        print("[SESSION] Submitting login...")
        # Try Enter first, then fall back to clicking the submit button.
        # Mobile web Instagram layout does not always honour keyboard Enter.
        page.keyboard.press("Enter")
        time.sleep(random.uniform(3, 5))
        if "login" in page.url:
            print("[SESSION] Enter didn't submit — trying Log in button click...")
            for btn_text in ["Log in", "Log In", "Login"]:
                try:
                    btn = page.locator(f'button:has-text("{btn_text}")')
                    if btn.is_visible(timeout=3000):
                        btn.click()
                        print(f"[SESSION] Clicked '{btn_text}' button.")
                        break
                except Exception:
                    pass
            time.sleep(random.uniform(5, 8))

        # Check for suspicious login alert
        try:
            suspicious = page.locator('button:has-text("This Was Me")')
            if suspicious.is_visible(timeout=5000):
                suspicious.click()
                time.sleep(3)
        except Exception:
            pass

        print(f"[SESSION] Post-submit URL: {page.url}")

        if "login" in page.url:
            _screenshot_login_state(page, "login_failed")
            send_telegram_alert(
                "INSTAGRAM LOGIN FAILED\n\n"
                "Wrong credentials or blocked.\n"
                "Check .env credentials."
            )
            return False

        # ── Code entry / verification challenge ───────────────────────────────
        # Instagram sends bots to /auth_platform/codeentry/ or /challenge/
        # after login. We relay the code through Telegram so it can be entered
        # without manual browser access.
        _CODE_URLS = [
            "codeentry",
            "auth_platform",
            "challenge",
            "checkpoint",
            "verify",
            "suspicious",
        ]
        if any(kw in page.url for kw in _CODE_URLS):
            _screenshot_login_state(page, "code_challenge")
            print(f"[SESSION] Code challenge detected: {page.url}")
            send_telegram_alert(
                "INSTAGRAM VERIFICATION CODE REQUIRED\n\n"
                "Instagram sent a code to the email or phone\n"
                "linked to afm_bot.\n\n"
                "Reply to this bot with JUST the 6-digit code\n"
                "(e.g. 123456) within 10 minutes."
            )
            code = _wait_for_telegram_code(timeout=600)
            if not code:
                send_telegram_alert(
                    "INSTAGRAM: No code received (10min timeout).\n"
                    "Monitor will pause and retry in 30 minutes."
                )
                return False
            # Find and fill the code input
            _code_selectors = [
                'input[name="verificationCode"]',
                'input[name="code"]',
                'input[autocomplete="one-time-code"]',
                'input[type="text"]',
                'input[type="number"]',
            ]
            code_input = None
            for sel in _code_selectors:
                try:
                    el = page.locator(sel).first
                    el.wait_for(timeout=5000)
                    code_input = el
                    print(f"[SESSION] Code input found via: {sel}")
                    break
                except Exception:
                    continue
            if not code_input:
                send_telegram_alert(
                    "INSTAGRAM: Could not find code input on challenge page.\n"
                    "Monitor will pause and retry in 30 minutes."
                )
                return False
            code_input.click()
            time.sleep(0.5)
            code_input.type(code, delay=120)
            time.sleep(1)
            page.keyboard.press("Enter")
            time.sleep(random.uniform(4, 6))
            # Try submit button if still on challenge
            if any(kw in page.url for kw in _CODE_URLS):
                for btn_text in ["Confirm", "Submit", "Continue", "Next", "Verify"]:
                    try:
                        btn = page.locator(f'button:has-text("{btn_text}")')
                        if btn.is_visible(timeout=3000):
                            btn.click()
                            time.sleep(random.uniform(4, 6))
                            break
                    except Exception:
                        pass
            if "login" in page.url or any(kw in page.url for kw in _CODE_URLS):
                send_telegram_alert(
                    "INSTAGRAM: Code entry failed or another challenge appeared.\n"
                    "Monitor will pause and retry in 30 minutes."
                )
                return False
            send_telegram_alert("Instagram code verified. Monitor is running.")

        # Dismiss prompts
        for text in ["Save Info", "Not Now", "Skip", "Cancel"]:
            try:
                btn = page.locator(f'button:has-text("{text}")')
                if btn.is_visible(timeout=3000):
                    btn.click()
                    time.sleep(random.uniform(1.5, 3))
            except Exception:
                pass

        print(f"[SESSION] Saving session at URL: {page.url}")
        save_session(context)
        print("[SESSION] Login successful.")
        send_telegram_alert("Instagram login successful.\nDM monitor is running.")
        return True

    except Exception as e:
        print(f"[SESSION] Login error: {e}")
        # Screenshot the failure state so we know what Instagram showed
        try:
            _screenshot_login_state(page, "login_error")
        except Exception:
            pass
        send_telegram_alert(f"INSTAGRAM LOGIN ERROR\n\n{str(e)[:300]}")
        return False


def handle_relogin(page, context):
    print("[SESSION] Session expired. Relogging...")
    send_telegram_alert("Instagram session expired.\nAttempting automatic relogin...")
    success = do_login(page, context)
    if not success:
        send_telegram_alert(
            "AUTO RELOGIN FAILED\n\n"
            "Check credentials in .env file.\n"
            "SSH: /opt/OS/services/.env"
        )
    return success


def check_inbox(page, context):
    if not session_is_valid(page):
        success = handle_relogin(page, context)
        if not success:
            print("[SESSION] Could not relogin. Skipping check.")
            return

    print("  Navigating to inbox...")
    page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
    time.sleep(random.uniform(2.0, 3.0))

    try:
        page.wait_for_selector("div[role='main']", timeout=60000)
    except Exception:
        print("  Could not load inbox main content.")
        return

    # Find conversation threads
    threads = []
    try:
        threads = page.query_selector_all('a[href*="/direct/t/"]')
    except Exception:
        pass
    if not threads:
        try:
            threads = page.query_selector_all('div[role="listitem"]')
        except Exception:
            pass

    if not threads:
        print("  No threads found in inbox.")
        return

    print(f"  Found {len(threads)} threads.")

    unread_indices = []
    for i, thread in enumerate(threads):
        try:
            is_unread = False
            # Check for aria-label containing "Unread"
            aria = thread.get_attribute("aria-label") or ""
            if "unread" in aria.lower():
                is_unread = True
            # Check for bold/strong child element indicating unread
            if not is_unread:
                bold = thread.query_selector(
                    "span[style*='font-weight: 700'], strong, b"
                )
                if bold:
                    is_unread = True
            # Check for unread dot/badge
            if not is_unread:
                badge = thread.query_selector(
                    'span[aria-label*="nread"], div[aria-label*="nread"]'
                )
                if badge:
                    is_unread = True
            if is_unread:
                unread_indices.append(i)
        except Exception:
            continue

    if not unread_indices:
        print("  No unread threads.")
        return

    print(f"  {len(unread_indices)} unread thread(s) found.")

    for idx in unread_indices:
        try:
            # Re-query threads since DOM may have changed
            threads = page.query_selector_all('a[href*="/direct/t/"]')
            if not threads:
                threads = page.query_selector_all('div[role="listitem"]')
            if idx >= len(threads):
                continue

            thread = threads[idx]
            time.sleep(random.uniform(1.5, 3.5))
            thread.click()
            time.sleep(random.uniform(2.0, 3.5))

            # Wait for messages to load
            try:
                page.wait_for_selector('div[dir="auto"]', timeout=15000)
            except Exception:
                print(f"  Thread {idx}: messages did not load, skipping.")
                page.goto(
                    "https://www.instagram.com/direct/inbox/",
                    wait_until="domcontentloaded",
                )
                time.sleep(random.uniform(2.0, 3.0))
                continue

            # Extract username from header
            username = "unknown"
            try:
                header = page.query_selector("header")
                if header:
                    header_text = header.inner_text().strip()
                    for line in header_text.splitlines():
                        line = line.strip()
                        if line and line not in ("", "Instagram"):
                            username = line.split("\n")[0].strip()
                            break
            except Exception:
                pass

            # --- DOM extraction ---
            dom_messages = []
            try:
                msg_elements = page.query_selector_all('div[dir="auto"]')
                for el in msg_elements[-20:]:
                    text = el.inner_text().strip()
                    if text and len(text) > 1:
                        dom_messages.append(text)
                dom_messages = dom_messages[-10:]
                if dom_messages:
                    print(f"  [DOM] Extracted {len(dom_messages)} messages via DOM")
            except Exception as e:
                print(f"  [DOM] Extraction failed: {e}")

            last_message_dom = dom_messages[-1] if dom_messages else "(no message)"

            # TASK 5 — skip if no new activity since last check
            prior = conversation_states.get(username, {})
            if prior.get("last_message") == last_message_dom and prior.get(
                "last_message_count"
            ) == len(dom_messages):
                print(f"  @{username} — no new messages since last check — skipping")
                page.goto(
                    "https://www.instagram.com/direct/inbox/",
                    wait_until="domcontentloaded",
                )
                time.sleep(random.uniform(2.0, 3.0))
                continue

            # Take screenshot (only for threads with new activity)
            os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(SCREENSHOTS_DIR, f"dm_{username}_{ts}.png")
            try:
                page.screenshot(path=screenshot_path)
            except Exception as e:
                print(f"  Screenshot failed: {e}")
                screenshot_path = None

            # --- Gemini Vision fallback if DOM extraction is weak ---
            extraction_method = "DOM"
            if len(dom_messages) < 2 and screenshot_path:
                print(
                    f"  [GEMINI] DOM extraction weak ({len(dom_messages)} msgs), trying Vision..."
                )
                vision_msgs = extract_messages_from_screenshot(screenshot_path)
                if vision_msgs:
                    print(
                        f"  [GEMINI] Extracted {len(vision_msgs)} messages via Vision"
                    )
                    extraction_method = "GEMINI"
                    conversation_text = "\n".join(
                        f"{'Me' if m['sender'] == 'me' else 'Them'}: {m['text']}"
                        for m in vision_msgs
                    )
                    messages = [m["text"] for m in vision_msgs]
                else:
                    print(f"  [WARN] Both extraction methods failed for @{username}")
                    conversation_text = "\n".join(dom_messages)
                    messages = dom_messages
            else:
                conversation_text = "\n".join(dom_messages)
                messages = dom_messages

            last_message = messages[-1] if messages else "(no message)"

            # Detect stage and generate reply
            stage = detect_stage(conversation_text)
            suggested_reply = generate_reply(conversation_text)

            # Update conversation state tracker
            conversation_states[username] = {
                "last_message": last_message,
                "last_message_count": len(messages),
                "last_stage": stage,
                "extraction_method": extraction_method,
            }

            # TASK 2 + 4 — advance pipeline card based on stage
            pipeline_status, ready_alert = _advance_pipeline(username, stage)

            # Publish lead_replied event — triggers objection_handler async
            try:
                from runtime.event_bus import EventBus

                interaction_row = _mem.get_interaction_for_lead(
                    username, venture_id="lyfe_institute"
                )
                EventBus().publish_async(
                    "lead_replied",
                    {
                        "username": username,
                        "message": last_message,
                        "interaction_id": interaction_row["id"]
                        if interaction_row
                        else None,
                        "venture_id": "lyfe_institute",
                    },
                )
            except Exception as _eb_err:
                print(
                    f"  [EVENT BUS] lead_replied publish failed for @{username}: {_eb_err}"
                )

            # Build analysis block
            analysis = (
                f"**Stage:** {stage}\n\n"
                f"**Last message:** {last_message}\n\n"
                f"**Suggested reply:** {suggested_reply}\n\n"
                f"**Pipeline:** {pipeline_status}"
            )

            # Save conversation
            save_conversation(username, conversation_text, stage, analysis)

            # TASK 3 — updated Telegram notification with pipeline status
            notification = (
                f"\U0001f4ac New reply from @{username}\n\n"
                f'Their message:\n"{last_message}"\n\n'
                f'Suggested reply:\n"{suggested_reply}"\n\n'
                f"Stage: {stage}\n"
                f"Pipeline: {pipeline_status}\n\n"
                f"Open Instagram \u2192 search @{username} \u2192 copy reply \u2192 send"
            )
            send_telegram(notification)

            # Also alert Discord #outreach channel
            send_discord_webhook("DISCORD_OUTREACH_WEBHOOK", notification)

            # TASK 4 — fire call-invite alert if stage is Ready
            if ready_alert:
                send_telegram(ready_alert)
                send_discord_webhook("DISCORD_OUTREACH_WEBHOOK", ready_alert)

            print(
                f"  @{username} — {stage} — {pipeline_status} — [{extraction_method}] — notified."
            )

            # Return to inbox
            time.sleep(random.uniform(1.5, 3.5))
            page.goto(
                "https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded"
            )
            time.sleep(random.uniform(2.0, 3.0))

        except Exception as e:
            print(f"  Error processing thread {idx}: {e}")
            try:
                page.goto(
                    "https://www.instagram.com/direct/inbox/",
                    wait_until="domcontentloaded",
                )
                time.sleep(2.0)
            except Exception:
                pass
            continue

    # Save cookies after successful inbox read
    save_session(context)


def is_login_page(page):
    try:
        return page.query_selector('input[name="username"]') is not None
    except Exception:
        return False


def _clear_stale_chromium_session():
    """Clear the Chromium user-data dir if older than 7 days to prevent stale profile issues."""
    import shutil

    session_dir = os.path.join(get_vault_path(), "services", "instagram_session")
    if os.path.exists(session_dir):
        age_days = (
            datetime.datetime.now().timestamp() - os.path.getmtime(session_dir)
        ) / 86400
        if age_days > 7:
            try:
                shutil.rmtree(session_dir)
                os.makedirs(session_dir, exist_ok=True)
                print(f"[SESSION] Cleared {age_days:.1f}d old Chromium session dir")
            except Exception as e:
                print(f"[SESSION] Could not clear session dir: {e}")


def main():
    # Startup backoff: prevents tight Docker restart loops from piling up
    # Chromium instances (each ~700MB). OOM kill was caused by rapid restarts,
    # not Whisper. This 90s delay ensures each cycle has a clean slate.
    _clear_stale_chromium_session()

    startup_delay = int(os.getenv("MONITOR_STARTUP_DELAY", "90"))
    if startup_delay > 0:
        print(f"[STARTUP] Waiting {startup_delay}s before browser launch...")
        time.sleep(startup_delay)

    with sync_playwright() as p:
        # Proxy is opt-in via INSTAGRAM_USE_PROXY=true.
        # Apify RESIDENTIAL proxy returns 403 when credits/plan are depleted —
        # VPS has direct Instagram access so proxy is not required.
        use_proxy = os.getenv("INSTAGRAM_USE_PROXY", "false").lower() == "true"
        apify_pass = os.getenv("APIFY_PROXY_PASSWORD")
        launch_kwargs: dict = dict(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        if use_proxy and apify_pass:
            sticky_id = uuid.uuid4().hex[:8]
            print(f"[SESSION] Proxy sticky session: {sticky_id}")
            launch_kwargs["proxy"] = {
                "server": "http://proxy.apify.com:8000",
                "username": f"groups-RESIDENTIAL,session-{sticky_id},country-US",
                "password": apify_pass,
            }
        else:
            print(
                "[SESSION] Direct connection (set INSTAGRAM_USE_PROXY=true to enable Apify proxy)."
            )

        browser = p.chromium.launch(**launch_kwargs)

        # Desktop Chrome UA — mobile Safari UA causes Instagram to serve a blank
        # page in headless Chromium (app-redirect / deep-link path). Desktop is
        # confirmed to render the login form correctly.
        _ctx_kwargs = dict(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/Los_Angeles",
        )

        # CAUSE 3 FIX: storage_state saves cookies + localStorage together.
        # Instagram auth lives in both — cookie-only restore leaves sessions
        # incomplete, triggering bot detection on the first real request.
        session_path = get_session_path()
        context = None
        page = None

        if load_session_exists():
            try:
                context = browser.new_context(storage_state=session_path, **_ctx_kwargs)
                page = context.new_page()
                if session_is_valid(page):
                    print("[SESSION] Session restored from storage state.")
                else:
                    print("[SESSION] Storage state expired — logging in fresh.")
                    context.close()
                    os.remove(session_path)
                    context = None
            except Exception as e:
                print(f"[SESSION] Could not restore storage state: {e}")
                if context:
                    context.close()
                    context = None
                try:
                    os.remove(session_path)
                except Exception:
                    pass

        if context is None:
            context = browser.new_context(**_ctx_kwargs)
            page = context.new_page()
            if not do_login(page, context):
                print(
                    "[SESSION] Cannot login. Pausing 30min then exiting for Docker restart."
                )
                _err.handle(
                    Exception("Instagram login failed at startup"),
                    context="instagram_login",
                    error_type="instagram_login",
                )
                time.sleep(1800)
                import sys

                sys.exit(1)

        print("Session ready. Starting inbox monitor.")
        print("Checking every ~5 minutes. Press Ctrl+C to stop.\n")

        cleanup_old_screenshots()

        consecutive_failures = 0
        PAUSE_AFTER_FAILURES = 3
        PAUSE_DURATION = 600  # 10 min pause before Docker restart

        while True:
            now = datetime.datetime.now().strftime("%I:%M %p")
            print(f"[{now}] Checking inbox...")
            try:
                check_inbox(page, context)
                consecutive_failures = 0  # reset on success
            except Exception as e:
                consecutive_failures += 1
                print(
                    f"  Error during inbox check ({consecutive_failures}/{PAUSE_AFTER_FAILURES}): {e}"
                )
                _err.handle(e, context="check_inbox loop")
                if consecutive_failures >= PAUSE_AFTER_FAILURES:
                    print(
                        f"  [{PAUSE_AFTER_FAILURES} consecutive failures] Pausing {PAUSE_DURATION}s then exiting for Docker restart."
                    )
                    time.sleep(PAUSE_DURATION)
                    import sys

                    sys.exit(1)

            interval = random.uniform(270, 330)
            next_check = (
                datetime.datetime.now() + datetime.timedelta(seconds=interval)
            ).strftime("%I:%M %p")
            print(f"  Next check at ~{next_check}\n")
            time.sleep(interval)


if __name__ == "__main__":
    main()
