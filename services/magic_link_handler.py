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
    "claude": ["noreply@anthropic.com", "no-reply@anthropic.com", "anthropic.com"],
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


def _get_gws_connector():
    """Import and return GWSConnector instance."""
    from adapters.google_workspace.gws_connector import GWSConnector
    return GWSConnector()


def _get_full_message_body(gws, message_id: str) -> str:
    """Fetch full message body (HTML or plain text) from Gmail API."""
    detail = gws._run(
        "gmail", "users", "messages", "get",
        params={
            "userId": "me",
            "id": message_id,
            "format": "full",
        },
    )
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
        gws = _get_gws_connector()
    except Exception as exc:
        logger.error("[MagicLink] Cannot initialize GWSConnector: %s", exc)
        return web.json_response(
            {"ok": False, "error": f"gmail connector failed: {exc}"},
            status=500,
        )

    senders = _SENDER_PATTERNS[service]
    subjects = _SUBJECT_PATTERNS.get(service, [])

    while (time.time() - start_time) < timeout:
        try:
            for sender in senders:
                query = f"from:{sender} newer_than:5m"
                emails = gws.get_recent_emails(max_results=5, query=query)

                for msg in emails:
                    msg_id = msg.get("id", "")
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)

                    subject = msg.get("subject", "").lower()
                    date_str = msg.get("date", "")

                    if not _is_recent_email(date_str):
                        continue

                    subject_match = any(kw in subject for kw in subjects)
                    if not subject_match:
                        continue

                    logger.info(
                        "[MagicLink] Found candidate email: id=%s subject='%s' from=%s",
                        msg_id, msg.get("subject", ""), sender,
                    )

                    body = _get_full_message_body(gws, msg_id)
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
