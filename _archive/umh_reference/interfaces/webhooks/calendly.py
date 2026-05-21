import os
import json
import hmac
import hashlib
import datetime
import glob
import re
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import sys as _sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in _sys.path:
    _sys.path.insert(0, _REPO_ROOT)
from umh.runtime_engine.memory import AgentMemory

_mem = AgentMemory()


def _log_calendly_outcome(username, outcome_type, score, notes=None):
    """Wire Calendly events to memory.db. Silent on failure."""
    try:
        row = _mem.get_interaction_for_lead(username, venture_id="lyfe_institute")
        if row:
            _mem.log_outcome(row["id"], outcome_type, score=score, notes=notes)
        else:
            _mem.log_orphaned_reply(
                username,
                outcome_type=outcome_type,
                score=score,
                notes=notes or "calendly event — no interaction in memory.db",
            )
    except Exception as e:
        print(f"[RLHF] calendly outcome log failed for {username}: {e}")


VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY")
PIPELINE_FILE = os.path.join(VAULT, "03_CRM/Pipeline.md")
LEADS_DIR = os.path.join(VAULT, "03_CRM/Leads")

app = Flask(__name__)

# Mount Higgsfield webhook route on the same Flask app so os-webhook
# (docker container, port 8080) handles /webhooks/higgsfield too.
try:
    from umh.interfaces.webhooks.higgsfield import register as _register_higgsfield

    _register_higgsfield(app)
except Exception as _e:
    print(f"[calendly_webhook] higgsfield webhook mount failed: {_e}")


def _detect_venture_from_event(event_name: str) -> str:
    """Detect venture from Calendly event name."""
    name = event_name.lower()
    if any(k in name for k in ["lyfe", "initiate", "arena", "coaching"]):
        return "Lyfe Institute"
    if any(k in name for k in ["brand", "content", "antony"]):
        return "Personal Brand"
    return "Empyrean Creative"  # default for B2B


def verify_signature(payload, signature):
    if not CALENDLY_SIGNING_KEY:
        return True
    expected = hmac.new(
        CALENDLY_SIGNING_KEY.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=10,
    )


def find_lead_by_name_or_email(name, email):
    lead_files = glob.glob(os.path.join(LEADS_DIR, "lead_*.md"))
    name_lower = name.lower() if name else ""
    email_lower = email.lower() if email else ""
    for filepath in lead_files:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        content_lower = content.lower()
        if (name_lower and name_lower in content_lower) or (
            email_lower and email_lower in content_lower
        ):
            return filepath
    return None


def move_pipeline_card(username, from_stage, to_stage):
    if not os.path.exists(PIPELINE_FILE):
        return False
    with open(PIPELINE_FILE, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    card_line = None
    card_idx = None
    current_section = None
    for i, line in enumerate(lines):
        if line.startswith("## "):
            current_section = line[3:].strip()
        elif current_section == from_stage and username.lower() in line.lower():
            card_line = line
            card_idx = i
            break
    if card_line is None:
        return False
    lines.pop(card_idx)
    for i, line in enumerate(lines):
        if line.startswith(f"## {to_stage}"):
            insert_at = i + 3
            lines.insert(insert_at, card_line)
            break
    with open(PIPELINE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True


def update_lead_file(filepath, new_stage, event_time=None, cancel_reason=None):
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r"^kanban_stage:.*", f"kanban_stage: {new_stage}", content, flags=re.MULTILINE
    )
    content = re.sub(
        r"^status:.*", f"status: {new_stage.lower()}", content, flags=re.MULTILINE
    )
    today = datetime.date.today().isoformat()
    if event_time:
        content += f"\n\n## Call Booked\nDate: {event_time}\nLogged: {today}\n"
    if cancel_reason:
        content += f"\n\n## Call Canceled\nReason: {cancel_reason}\nLogged: {today}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


def update_notion_lead_stage(name: str, email: str, new_stage: str) -> bool:
    """Find a lead in the Notion Pipeline database by name or email and update their stage."""
    from dotenv import load_dotenv

    load_dotenv("/opt/OS/umh/.env")

    token = os.getenv("NOTION_API_KEY")
    db_id = os.getenv("NOTION_LYFE_PIPELINE_ID")
    if not token or not db_id:
        return False

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query",
            headers=headers,
            json={"page_size": 100},
            timeout=10,
        )
        if resp.status_code != 200:
            return False

        pages = resp.json().get("results", [])
        name_lower = name.lower() if name else ""
        email_lower = email.lower() if email else ""

        target_page_id = None
        for page in pages:
            title_list = page["properties"].get("Name", {}).get("title", [])
            page_name = title_list[0]["text"]["content"].lower() if title_list else ""
            if name_lower and name_lower in page_name:
                target_page_id = page["id"]
                break
            if email_lower and email_lower in page_name:
                target_page_id = page["id"]
                break

        if not target_page_id:
            print(f"[Notion] No page found for {name} / {email}")
            return False

        update_resp = requests.patch(
            f"https://api.notion.com/v1/pages/{target_page_id}",
            headers=headers,
            json={
                "properties": {
                    "Stage": {"select": {"name": new_stage}},
                    "Last Contact": {
                        "date": {"start": datetime.date.today().isoformat()}
                    },
                }
            },
            timeout=10,
        )
        success = update_resp.status_code == 200
        if success:
            print(f"[Notion] {name} → {new_stage}")
        return success

    except Exception as e:
        print(f"[Notion] update_notion_lead_stage failed: {e}")
        return False


@app.route("/webhooks/calendly", methods=["POST"])
def calendly_webhook():
    signature = request.headers.get("Calendly-Webhook-Signature", "")
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401

    data = request.json
    event_type = data.get("event")
    payload = data.get("payload", {})
    invitee = payload.get("invitee", {})
    name = invitee.get("name", "Unknown")
    email = invitee.get("email", "")
    event_time = payload.get("event", {}).get("start_time", "")

    if event_type == "invitee.created":
        lead_file = find_lead_by_name_or_email(name, email)
        username = name
        if lead_file:
            update_lead_file(lead_file, "Booked", event_time=event_time)
            filename = os.path.basename(lead_file)
            username = filename.replace("lead_", "").split("_")[0]
            move_pipeline_card(username, "Qualifying", "Booked")
            move_pipeline_card(username, "Replied", "Booked")
        _log_calendly_outcome(
            username, "booked", 1.0, notes=f"Calendly invitee.created — {event_time}"
        )
        # Publish lead_booked event — triggers handler async (non-blocking)
        try:
            from umh.runtime_engine.event_bus import get_bus

            get_bus().publish_async(
                "lead_booked",
                {
                    "username": username,
                    "booking_time": event_time,
                    "venture_id": "lyfe_institute",
                },
            )
        except Exception as _eb_err:
            print(f"[EVENT BUS] lead_booked publish failed for {username}: {_eb_err}")
        update_notion_lead_stage(name, email, "Booked")
        send_telegram(
            f"CALL BOOKED\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Time: {event_time}\n\n"
            f"Card moved to Booked in Pipeline."
        )

        # Person recognition — Martell rule check before anything else
        try:
            from umh.runtime_engine.person_recognition import (
                recognize_person,
                format_person_context,
            )

            _recognition = recognize_person(name=name, email=email)
            _person_context = format_person_context(_recognition, name=name)
            if _recognition.get("warning"):
                print(f"[Calendly] {_recognition['warning']}")
        except Exception as _pr_err:
            _recognition = {}
            _person_context = ""
            print(f"[Calendly] Person recognition failed: {_pr_err}")

        # Create meeting record (Neon + Notion)
        try:
            from umh.runtime_engine.meetings import create_meeting_record, build_prep_brief

            _invitee = payload.get("invitee", {})
            _event_obj = payload.get("event", {})
            _questions = _invitee.get("questions_and_answers", [])
            _company = next(
                (
                    q["answer"]
                    for q in _questions
                    if "company" in q.get("question", "").lower()
                ),
                "",
            )
            _venture = _detect_venture_from_event(_event_obj.get("name", ""))
            _meet_link = (
                _event_obj.get("location", {}).get("join_url", "")
                if isinstance(_event_obj.get("location"), dict)
                else ""
            )
            _cal_event_id = _event_obj.get("uuid", "")

            _record = create_meeting_record(
                title=_event_obj.get("name", "Call"),
                person=name,
                email=email,
                company=_company,
                date_iso=event_time,
                meeting_type="Sales Call",
                venture=_venture,
                source="Calendly",
                meet_link=_meet_link,
                calendly_event_id=_cal_event_id,
            )
            print(
                f"[Calendly] Meeting record: neon={_record.get('neon_id')} notion={_record.get('notion_id')}"
            )
        except Exception as _mr_err:
            print(f"[Calendly] Meeting record failed: {_mr_err}")
            _record = {}
            _company = ""
            _venture = "Empyrean Creative"
            _meet_link = ""

        # Auto-create lead file if no existing one found
        if not lead_file:
            try:
                from umh.runtime_engine.person_recognition import create_lead_file

                create_lead_file(
                    name=name,
                    email=email,
                    company=_company,
                    source="calendly",
                    venture=_venture,
                )
            except Exception as e:
                print(f"[Calendly] Lead file creation failed: {e}")

        # Send Discord alert with prep brief
        try:
            _discord_webhook = os.getenv("DISCORD_BRIEF_WEBHOOK") or os.getenv(
                "DISCORD_WEBHOOK_URL"
            )
            if _discord_webhook:
                import requests as _req

                _brief = build_prep_brief(
                    person=name,
                    email=email,
                    company=_company,
                    meeting_type="Sales Call",
                    venture=_venture,
                )
                _known_flag = (
                    " 🔴 **KNOWN PERSON**" if _recognition.get("known") else ""
                )
                _msg = (
                    f"📅 **New booking: {name}**{_known_flag}\n"
                    f"🕐 {event_time}\n"
                    f"🏢 {_company or 'No company listed'}\n\n"
                    f"{_brief}"
                )
                if _person_context:
                    _msg += f"\n\n{_person_context}"
                from umh.runtime_engine.discord_utils import post_to_webhook

                post_to_webhook(_msg, username="DEX", webhook_url=_discord_webhook)
        except Exception as _disc_err:
            print(f"[Calendly] Discord alert failed: {_disc_err}")

        return jsonify({"status": "booked"}), 200

    elif event_type == "invitee.canceled":
        cancel_reason = payload.get("cancellation", {}).get("reason", "No reason given")
        lead_file = find_lead_by_name_or_email(name, email)
        if lead_file:
            update_lead_file(lead_file, "Lost", cancel_reason=cancel_reason)
            filename = os.path.basename(lead_file)
            username = filename.replace("lead_", "").split("_")[0]
            move_pipeline_card(username, "Booked", "Lost")
        _log_calendly_outcome(
            name, "no_reply", 0.0, notes=f"Calendly canceled — {cancel_reason}"
        )
        send_telegram(
            f"CALL CANCELED\n\n"
            f"Name: {name}\n"
            f"Reason: {cancel_reason}\n\n"
            f"Card moved to Lost."
        )

        # Cancellation recovery flow
        try:
            import os as _os
            from umh.gateway.entry import utility_llm_call

            _inv = data.get("payload", {}).get("invitee", {})
            _ev = data.get("payload", {}).get("event", {})
            _cname = _inv.get("name", "there")
            _cemail = _inv.get("email", "")
            _event_name = _ev.get("name", "our call")

            _draft = utility_llm_call(
                prompt=f"""Draft a brief, warm re-engagement email for someone who cancelled a meeting.

Person: {_cname}
Meeting: {_event_name}

Antony's voice — direct, warm, no pressure.
Offer to reschedule, include Calendly link placeholder.
Under 5 sentences.

Format:
Subject: [subject]
[body]
DEX
On behalf of Antony Munoz""",
                operation="cancellation_recovery",
            ).strip()

            from umh.environments.system_context import load_context_from_env
            from umh.storage.adapters.neon import get_conn
            import json as _json

            _ctx = load_context_from_env()
            with get_conn(_ctx.org_id) as _cur:
                _cur.execute(
                    """
                    INSERT INTO events
                    (org_id, event_type, payload_json, handled_by)
                    VALUES (%s, %s, %s, %s)
                """,
                    (
                        str(_ctx.org_id),
                        "email_draft_pending",
                        _json.dumps(
                            {
                                "draft": _draft,
                                "to_email": _cemail,
                                "to_name": _cname,
                                "type": "cancellation_recovery",
                                "status": "pending_approval",
                            }
                        ),
                        "dex_calendly",
                    ),
                )

            import requests as _req

            _webhook = _os.getenv("DISCORD_BRIEF_WEBHOOK")
            if _webhook:
                _msg = (
                    f"❌ **Cancelled: {_cname}**\n"
                    f"Re-engagement email drafted:\n"
                    f"```\n{_draft[:600]}\n```\n"
                    f"`!approve_followup` to send."
                )
                from umh.runtime_engine.discord_utils import post_to_webhook as _post_webhook

                _post_webhook(_msg, username="DEX", webhook_url=_webhook)

        except Exception as e:
            print(f"[Calendly] Cancellation recovery failed: {e}")

        return jsonify({"status": "canceled"}), 200

    return jsonify({"status": "ignored"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
