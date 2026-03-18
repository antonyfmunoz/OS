import os
import sys
import json
import glob
import time
import random
import datetime
import base64
import requests
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cost_tracker

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
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_DIR = os.path.join(VAULT, "13_Scripts", "instagram_session")
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
    path = os.path.join(VAULT, "05_Workflows", "Sales", "conversation_assistant", filename)
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
            if stripped.startswith(("- [ ]", "- [x]")) and username.lower() in stripped.lower():
                card_idx = i
                break

    if card_idx is None:
        # Check if card exists in any other section (already moved — skip)
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- [ ]", "- [x]")) and username.lower() in stripped.lower():
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
    fields_written = {"kanban_stage": False, "status": False,
                      "conversation_stage": False, "last_stage_update": False}

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
    return meta, content[end + 3:].strip()


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
    config_path = os.path.join(vault, "13_Scripts/hashtag_config.json")
    if not os.path.exists(config_path):
        return
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
        perf = config.get("performance", {})
        if source in perf:
            perf[source]["booked_count"] = perf[source].get("booked_count", 0) + 1
            total = perf[source].get("total_qualified", 1)
            perf[source]["booking_rate"] = round(perf[source]["booked_count"] / total, 4)
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
        config_path = os.path.join(vault, "13_Scripts/hashtag_config.json")
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
        opener_stats_path = os.path.join(vault, "13_Scripts/opener_stats.json")
        try:
            if os.path.exists(opener_stats_path):
                with open(opener_stats_path, encoding="utf-8") as f:
                    stats = json.load(f)
            else:
                stats = {"openers": {}}
            openers = stats.setdefault("openers", {})
            openers.setdefault(opener_sent, {"sent": 0, "replies": 0, "reply_rate": 0.0})
            openers[opener_sent]["replies"] += 1
            sent = openers[opener_sent]["sent"]
            replies = openers[opener_sent]["replies"]
            if sent > 0:
                openers[opener_sent]["reply_rate"] = round(replies / sent, 4)
            with open(opener_stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            print(f"  [REPLY TRACK] Opener update failed: {e}")


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
            pipeline_status = (pipeline_status + " → Qualifying") if pipeline_status else "→ Qualifying"
            print(f"  [PIPELINE] @{username} → Qualifying")

    if stage == "Booked":
        moved = move_card_to_stage(username, "Qualifying", "Booked")
        if moved:
            update_lead_stage(username, "Booked", conversation_stage=stage)
            pipeline_status = (pipeline_status + " → Booked") if pipeline_status else "→ Booked"
            update_source_booked(username)
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
            f"\"Want to see if it\u2019s a fit? "
            f"I can jump on a quick call this week.\""
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
    if any(w in text_lower for w in ["let's hop on", "book a call", "schedule", "zoom", "calendly"]):
        return "Booked"
    if any(w in text_lower for w in ["how long", "what does that cost", "what's included", "tell me more about"]):
        return "Qualifying"
    # Ready = ownership + urgency — all 3 call-invite signals present
    if any(w in text_lower for w in ["i'm ready", "i need to fix this", "ready to commit",
                                      "what do i need to do", "how do i get started",
                                      "i want to change", "i'm done wasting", "sign me up"]):
        return "Ready"
    if any(w in text_lower for w in ["i feel", "i keep", "i can't", "i never", "i always", "i'm struggling"]):
        return "Diagnosing"
    if any(w in text_lower for w in ["yeah", "true", "exactly", "i know", "honestly"]):
        return "Engaged"
    return "Cold"


def generate_reply(conversation_text):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    extra_context = load_workflow_prompt("2_analyze_conversation.md")
    extra_context += "\n\n" + load_workflow_prompt("3_generate_response.md")

    system = SALES_SYSTEM_PROMPT
    if extra_context.strip():
        system += f"\n\n---\nADDITIONAL CONTEXT:\n{extra_context}"

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system,
            messages=[
                {"role": "user", "content": f"Here is the conversation so far. Suggest the best next reply (1-3 sentences max):\n\n{conversation_text}"}
            ],
        )
        input_tok = message.usage.input_tokens
        output_tok = message.usage.output_tokens
        cost_tracker.log_copilot_costs(
            sonnet_calls=1,
            sonnet_input_tokens=input_tok,
            sonnet_output_tokens=output_tok,
        )
        return message.content[0].text.strip()
    except Exception as e:
        print(f"Claude API error: {e}")
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
    screenshots_dir = os.path.join(
        get_vault_path(),
        "03_CRM/Conversations/screenshots"
    )
    if not os.path.exists(screenshots_dir):
        return
    cutoff = datetime.datetime.now() - \
             datetime.timedelta(days=30)
    removed = 0
    for filepath in glob.glob(
            os.path.join(screenshots_dir, "*.png")):
        try:
            mtime = datetime.datetime.fromtimestamp(
                os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                removed += 1
        except Exception:
            pass
    if removed > 0:
        print(f"[CLEANUP] Removed {removed} "
              f"screenshots older than 30 days")


def send_telegram_alert(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/"
            f"bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except Exception:
        pass


def get_session_path():
    return os.path.join(
        get_vault_path(),
        "13_Scripts/instagram_session.json")


def save_session(context):
    try:
        cookies = context.cookies()
        with open(get_session_path(), "w") as f:
            json.dump(cookies, f)
        print("[SESSION] Cookies saved.")
    except Exception as e:
        print(f"[SESSION] Could not save cookies: {e}")


def load_session(context):
    path = get_session_path()
    if not os.path.exists(path):
        return False
    try:
        with open(path) as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        print("[SESSION] Cookies loaded.")
        return True
    except Exception as e:
        print(f"[SESSION] Could not load cookies: {e}")
        return False


def session_is_valid(page):
    try:
        page.goto(
            "https://www.instagram.com/direct/inbox/",
            wait_until="domcontentloaded",
            timeout=60000)
        time.sleep(3)
        if "login" in page.url:
            return False
        return True
    except Exception:
        return False


def do_login(page, context):
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")
    if not username or not password:
        send_telegram_alert(
            "INSTAGRAM LOGIN FAILED\n\n"
            "Missing credentials in .env")
        return False
    try:
        # Go directly to login page
        page.goto(
            "https://www.instagram.com/accounts/login/",
            wait_until="domcontentloaded",
            timeout=60000)
        time.sleep(8)

        # Dismiss cookie consent if present
        try:
            for text in ["Allow all cookies",
                         "Accept All",
                         "Allow essential and optional cookies"]:
                btn = page.locator(
                    f'button:has-text("{text}")')
                if btn.is_visible(timeout=3000):
                    btn.click()
                    time.sleep(2)
                    break
        except Exception:
            pass

        # If not on login page navigate there
        if "login" not in page.url:
            page.goto(
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
                timeout=60000)
            time.sleep(5)

        # Wait for page to fully render
        time.sleep(20)
        page.fill('input[name="username"]', username)
        time.sleep(1)
        page.fill('input[name="password"]', password)
        time.sleep(1)
        page.click('button[type="submit"]')
        time.sleep(8)

        # Check for suspicious login alert
        try:
            suspicious = page.locator(
                'button:has-text("This Was Me")')
            if suspicious.is_visible(timeout=5000):
                suspicious.click()
                time.sleep(3)
        except Exception:
            pass

        # Check for 2FA
        try:
            twofa = page.locator(
                'input[name="verificationCode"]')
            if twofa.is_visible(timeout=5000):
                send_telegram_alert(
                    "INSTAGRAM 2FA REQUIRED\n\n"
                    "Check your email or phone\n"
                    "for verification code.\n"
                    "2FA must be disabled for\n"
                    "auto-login to work.")
                # Wait up to 5 min for manual entry
                for _ in range(60):
                    time.sleep(5)
                    if "login" not in page.url:
                        break
        except Exception:
            pass

        if "login" in page.url:
            send_telegram_alert(
                "INSTAGRAM LOGIN FAILED\n\n"
                "Wrong credentials or blocked.\n"
                "Check .env credentials.")
            return False

        # Dismiss prompts
        for text in ["Save Info", "Not Now",
                     "Skip", "Cancel"]:
            try:
                btn = page.locator(
                    f'button:has-text("{text}")')
                if btn.is_visible(timeout=3000):
                    btn.click()
                    time.sleep(2)
            except Exception:
                pass

        save_session(context)
        print("[SESSION] Login successful.")
        send_telegram_alert(
            "Instagram login successful.\n"
            "DM monitor is running.")
        return True

    except Exception as e:
        print(f"[SESSION] Login error: {e}")
        send_telegram_alert(
            f"INSTAGRAM LOGIN ERROR\n\n"
            f"{str(e)[:300]}")
        return False


def handle_relogin(page, context):
    print("[SESSION] Session expired. Relogging...")
    send_telegram_alert(
        "Instagram session expired.\n"
        "Attempting automatic relogin...")
    success = do_login(page, context)
    if not success:
        send_telegram_alert(
            "AUTO RELOGIN FAILED\n\n"
            "Check credentials in .env file.\n"
            "SSH: /opt/OS/13_Scripts/.env")
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
                bold = thread.query_selector("span[style*='font-weight: 700'], strong, b")
                if bold:
                    is_unread = True
            # Check for unread dot/badge
            if not is_unread:
                badge = thread.query_selector('span[aria-label*="nread"], div[aria-label*="nread"]')
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
                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
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
            if (prior.get("last_message") == last_message_dom
                    and prior.get("last_message_count") == len(dom_messages)):
                print(f"  @{username} — no new messages since last check — skipping")
                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
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
                print(f"  [GEMINI] DOM extraction weak ({len(dom_messages)} msgs), trying Vision...")
                vision_msgs = extract_messages_from_screenshot(screenshot_path)
                if vision_msgs:
                    print(f"  [GEMINI] Extracted {len(vision_msgs)} messages via Vision")
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
                f"Their message:\n\"{last_message}\"\n\n"
                f"Suggested reply:\n\"{suggested_reply}\"\n\n"
                f"Stage: {stage}\n"
                f"Pipeline: {pipeline_status}\n\n"
                f"Open Instagram \u2192 search @{username} \u2192 copy reply \u2192 send"
            )
            send_telegram(notification)

            # TASK 4 — fire call-invite alert if stage is Ready
            if ready_alert:
                send_telegram(ready_alert)

            print(f"  @{username} — {stage} — {pipeline_status} — [{extraction_method}] — notified.")

            # Return to inbox
            time.sleep(random.uniform(1.5, 3.5))
            page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
            time.sleep(random.uniform(2.0, 3.0))

        except Exception as e:
            print(f"  Error processing thread {idx}: {e}")
            try:
                page.goto("https://www.instagram.com/direct/inbox/", wait_until="domcontentloaded")
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


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox'],
            proxy={
                'server': 'http://proxy.apify.com:8000',
                'username': 'groups-RESIDENTIAL',
                'password': os.getenv('APIFY_PROXY_PASSWORD')
            }
        )
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/Los_Angeles',
        )
        page = context.new_page()

        # Try restoring saved session first
        session_loaded = load_session(context)
        if session_loaded and session_is_valid(page):
            print("[SESSION] Session restored.")
        else:
            if session_loaded:
                print("[SESSION] Saved session expired.")
            else:
                print("[SESSION] No saved session.")
            if not do_login(page, context):
                print("[SESSION] Cannot login. Exiting.")
                browser.close()
                return

        print("Session ready. Starting inbox monitor.")
        print("Checking every ~5 minutes. Press Ctrl+C to stop.\n")

        cleanup_old_screenshots()

        while True:
            now = datetime.datetime.now().strftime("%I:%M %p")
            print(f"[{now}] Checking inbox...")
            try:
                check_inbox(page, context)
            except Exception as e:
                print(f"  Error during inbox check: {e}")

            interval = random.uniform(270, 330)
            next_check = (datetime.datetime.now() + datetime.timedelta(seconds=interval)).strftime("%I:%M %p")
            print(f"  Next check at ~{next_check}\n")
            time.sleep(interval)


if __name__ == "__main__":
    main()
