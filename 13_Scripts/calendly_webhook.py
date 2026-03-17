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

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CALENDLY_SIGNING_KEY = os.getenv("CALENDLY_SIGNING_KEY")
PIPELINE_FILE = os.path.join(VAULT, "03_CRM/Pipeline.md")
LEADS_DIR = os.path.join(VAULT, "03_CRM/Leads")

app = Flask(__name__)


def verify_signature(payload, signature):
    if not CALENDLY_SIGNING_KEY:
        return True
    expected = hmac.new(
        CALENDLY_SIGNING_KEY.encode(),
        payload,
        hashlib.sha256
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
        if (name_lower and name_lower in content_lower) or \
           (email_lower and email_lower in content_lower):
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
        r'^kanban_stage:.*',
        f'kanban_stage: {new_stage}',
        content, flags=re.MULTILINE
    )
    content = re.sub(
        r'^status:.*',
        f'status: {new_stage.lower()}',
        content, flags=re.MULTILINE
    )
    today = datetime.date.today().isoformat()
    if event_time:
        content += f"\n\n## Call Booked\nDate: {event_time}\nLogged: {today}\n"
    if cancel_reason:
        content += f"\n\n## Call Canceled\nReason: {cancel_reason}\nLogged: {today}\n"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)


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
        send_telegram(
            f"CALL BOOKED\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n"
            f"Time: {event_time}\n\n"
            f"Card moved to Booked in Pipeline."
        )
        return jsonify({"status": "booked"}), 200

    elif event_type == "invitee.canceled":
        cancel_reason = payload.get("cancellation", {}).get("reason", "No reason given")
        lead_file = find_lead_by_name_or_email(name, email)
        if lead_file:
            update_lead_file(lead_file, "Lost", cancel_reason=cancel_reason)
            filename = os.path.basename(lead_file)
            username = filename.replace("lead_", "").split("_")[0]
            move_pipeline_card(username, "Booked", "Lost")
        send_telegram(
            f"CALL CANCELED\n\n"
            f"Name: {name}\n"
            f"Reason: {cancel_reason}\n\n"
            f"Card moved to Lost."
        )
        return jsonify({"status": "canceled"}), 200

    return jsonify({"status": "ignored"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
