"""magic_link_handler.py — Bridge endpoint for intercepting magic-link emails.

Watches Gmail for magic-link login emails from services (currently claude.ai).
Polls at short intervals, extracts the URL from the email body, returns it
to the auth flow module which navigates Camoufox to the link directly.

Architecture:
    auth_flows/claude.py → POST /api/auth/wait-for-magic-link
    → This handler polls Gmail via GWSConnector for matching email
    → Extracts magic-link URL from HTML body
    → Returns {"magic_link_url": "https://..."} to caller
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from aiohttp import web

_REPO_ROOT = Path(os.getenv("EOS_REPO_ROOT", str(Path.home() / "dev" / "OSv2")))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger("magic_link_handler")

_SENDER_PATTERNS: dict[str, list[str]] = {
    "claude": ["mail.anthropic.com", "noreply@anthropic.com", "no-reply@anthropic.com", "anthropic.com"],
}

_SUBJECT_PATTERNS: dict[str, list[str]] = {
    "claude": ["sign in", "log in", "login", "magic link", "verify", "claude"],
}

_URL_PATTERNS: dict[str, list[str]] = {
    "claude": [
        r"https://claude\.ai/magic-link[^\s\"'<>]+",
        r"https://claude\.ai/auth[^\s\"'<>]+",
        r"https://claude\.ai/login/callback[^\s\"'<>]+",
        r"https://console\.anthropic\.com/auth[^\s\"'<>]+",
    ],
}

_POLL_INTERVAL_S = 5
_MAX_EMAIL_AGE_S = 180
_GMAIL_CREDS_PATH = Path("/root/.config/gws/gmail_credentials.json")


def _get_gmail_service():
    """Build Gmail API service using stored OAuth credentials."""
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not _GMAIL_CREDS_PATH.exists():
        raise RuntimeError(
            f"Gmail credentials not found at {_GMAIL_CREDS_PATH}. "
            "Run: python3 services/oauth_device_flow.py --scopes gmail.readonly"
        )

    data = json.loads(_GMAIL_CREDS_PATH.read_text())
    creds = Credentials(
        token=data.get("access_token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes", []),
    )
    return build("gmail", "v1", credentials=creds)


def _gmail_list_messages(service, query: str, max_results: int = 5) -> list[dict]:
    """List messages matching query via Gmail API."""
    results = service.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute()
    return results.get("messages", [])


def _gmail_get_message(service, message_id: str, fmt: str = "metadata") -> dict:
    """Get a single message by ID."""
    return service.users().messages().get(
        userId="me", id=message_id, format=fmt
    ).execute()


def _get_full_message_body(service, message_id: str) -> str:
    """Fetch full message body (HTML or plain text) from Gmail API."""
    detail = _gmail_get_message(service, message_id, fmt="full")
    if not detail:
        return ""
    payload = detail.get("payload", {})
    return _extract_body_from_payload(payload)


def _extract_body_from_payload(payload: dict) -> str:
    """Recursively extract body text from Gmail message payload."""
    body_data = payload.get("body", {}).get("data", "")
    if body_data:
        try:
            return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        except Exception:
            pass

    parts = payload.get("parts", [])
    for part in parts:
        mime_type = part.get("mimeType", "")
        if mime_type == "text/html":
            data = part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    pass
        elif mime_type == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                try:
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    pass
        elif "multipart" in mime_type:
            nested = _extract_body_from_payload(part)
            if nested:
                return nested

    return ""


def _extract_magic_link(body: str, service: str) -> str | None:
    """Extract magic-link URL from email body using service-specific patterns."""
    patterns = _URL_PATTERNS.get(service, [])
    for pattern in patterns:
        match = re.search(pattern, body)
        if match:
            url = match.group(0)
            url = url.rstrip(".")
            url = re.sub(r"&amp;", "&", url)
            return url

    # Fallback: any URL containing the service domain + auth-like path
    fallback_patterns = [
        rf"https://[^\s\"'<>]*{re.escape(service)}[^\s\"'<>]*(?:magic|auth|login|verify|callback)[^\s\"'<>]*",
    ]
    for pattern in fallback_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            url = match.group(0)
            url = url.rstrip(".")
            url = re.sub(r"&amp;", "&", url)
            return url

    return None


def _is_recent_email(date_str: str, max_age_s: int = _MAX_EMAIL_AGE_S) -> bool:
    """Check if an email date string is within the max age window."""
    from email.utils import parsedate_to_datetime
    try:
        email_dt = parsedate_to_datetime(date_str)
        age = time.time() - email_dt.timestamp()
        return age < max_age_s
    except Exception:
        return True


async def handle_wait_for_magic_link(request: web.Request) -> web.Response:
    """Poll Gmail for a magic-link email and return the URL.

    POST /api/auth/wait-for-magic-link
    Body: {"service": "claude", "email": "user@example.com", "timeout": 120}
    Response: {"magic_link_url": "https://...", "email_id": "...", "sender": "..."}
    """
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return web.json_response({"ok": False, "error": "invalid json"}, status=400)

    service = data.get("service", "").lower()
    email = data.get("email", "")
    timeout = min(data.get("timeout", 120), 300)

    if not service or service not in _SENDER_PATTERNS:
        return web.json_response(
            {"ok": False, "error": f"unsupported service: {service}"},
            status=400,
        )

    logger.info(
        "[MagicLink] Watching for %s magic-link email (timeout=%ds, recipient=%s)",
        service, timeout, email,
    )

    start_time = time.time()
    seen_ids: set[str] = set()

    try:
        gmail = _get_gmail_service()
    except Exception as exc:
        logger.error("[MagicLink] Cannot initialize Gmail service: %s", exc)
        return web.json_response(
            {"ok": False, "error": f"gmail service failed: {exc}"},
            status=500,
        )

    senders = _SENDER_PATTERNS[service]
    subjects = _SUBJECT_PATTERNS.get(service, [])

    while (time.time() - start_time) < timeout:
        try:
            for sender in senders:
                query = f"from:{sender} newer_than:5m"
                messages = _gmail_list_messages(gmail, query, max_results=5)

                for msg_ref in messages:
                    msg_id = msg_ref.get("id", "")
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)

                    detail = _gmail_get_message(gmail, msg_id, fmt="metadata")
                    headers = {
                        h["name"]: h["value"]
                        for h in detail.get("payload", {}).get("headers", [])
                    }
                    subject = headers.get("Subject", "").lower()
                    date_str = headers.get("Date", "")

                    if not _is_recent_email(date_str):
                        continue

                    subject_match = any(kw in subject for kw in subjects)
                    if not subject_match:
                        continue

                    logger.info(
                        "[MagicLink] Found candidate email: id=%s subject='%s' from=%s",
                        msg_id, headers.get("Subject", ""), sender,
                    )

                    body = _get_full_message_body(gmail, msg_id)
                    if not body:
                        logger.warning("[MagicLink] Could not retrieve body for %s", msg_id)
                        continue

                    magic_url = _extract_magic_link(body, service)
                    if magic_url:
                        elapsed = time.time() - start_time
                        logger.info(
                            "[MagicLink] Extracted magic link in %.1fs: %s",
                            elapsed, magic_url[:80],
                        )
                        return web.json_response({
                            "ok": True,
                            "magic_link_url": magic_url,
                            "email_id": msg_id,
                            "sender": sender,
                            "elapsed_seconds": round(elapsed, 1),
                        })
                    else:
                        logger.warning(
                            "[MagicLink] Email matched but no URL extracted (id=%s)",
                            msg_id,
                        )

        except Exception as exc:
            logger.warning("[MagicLink] Poll iteration error: %s", exc)

        await asyncio.sleep(_POLL_INTERVAL_S)

    elapsed = time.time() - start_time
    logger.warning("[MagicLink] Timed out after %.1fs — no magic link found", elapsed)
    return web.json_response(
        {"ok": False, "error": "timeout", "elapsed_seconds": round(elapsed, 1)},
        status=408,
    )


def register_routes(app: web.Application) -> None:
    """Register magic-link auth routes on the bridge server."""
    app.router.add_post("/api/auth/wait-for-magic-link", handle_wait_for_magic_link)
    logger.info("[MagicLink] Route registered: POST /api/auth/wait-for-magic-link")
