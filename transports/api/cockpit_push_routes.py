"""Cockpit push notification routes — VAPID key exchange + subscription management.

Satellite module mounted in cockpit.py via Pattern B.
Sends Web Push notifications to subscribed operator browsers.

UMH transport layer. Instance-agnostic.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
_SUBSCRIPTIONS_PATH = os.path.join(_ROOT, "data", "push_subscriptions.json")

push_router: APIRouter = APIRouter()
_configured = False

try:
    from pywebpush import webpush, WebPushException  # type: ignore[import-untyped]

    _PYWEBPUSH_AVAILABLE = True
except ImportError:
    _PYWEBPUSH_AVAILABLE = False
    logger.debug("pywebpush not installed — push notifications disabled")


def configure(require_operator_dep: Any) -> None:
    """Configure push routes with auth dependency."""
    global _configured
    auth = [Depends(require_operator_dep)]

    push_router.add_api_route(
        "/push/vapid-key",
        _vapid_key,
        methods=["GET"],
        dependencies=auth,
    )
    push_router.add_api_route(
        "/push/subscribe",
        _subscribe,
        methods=["POST"],
        dependencies=auth,
    )
    push_router.add_api_route(
        "/push/unsubscribe",
        _unsubscribe,
        methods=["DELETE"],
        dependencies=auth,
    )
    push_router.add_api_route(
        "/push/test",
        _test_push,
        methods=["POST"],
        dependencies=auth,
    )
    _configured = True


def _load_subscriptions() -> list[dict[str, Any]]:
    try:
        with open(_SUBSCRIPTIONS_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_subscriptions(subs: list[dict[str, Any]]) -> None:
    Path(_SUBSCRIPTIONS_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(_SUBSCRIPTIONS_PATH, "w") as f:
        json.dump(subs, f, indent=2)


# ── Route Handlers ────────────────────────────────────────────────


async def _vapid_key(request: Request) -> dict[str, Any]:
    """GET /push/vapid-key — return public VAPID key for browser subscription."""
    public_key = os.environ.get("VAPID_PUBLIC_KEY", "")
    return {
        "public_key": public_key,
        "available": bool(public_key) and _PYWEBPUSH_AVAILABLE,
    }


async def _subscribe(request: Request) -> dict[str, Any]:
    """POST /push/subscribe — store push subscription."""
    body = await request.json()
    subscription = body.get("subscription")
    if not subscription or not subscription.get("endpoint"):
        return {"success": False, "error": "subscription with endpoint required"}

    subs = _load_subscriptions()
    existing_endpoints = {s.get("endpoint") for s in subs}
    if subscription.get("endpoint") not in existing_endpoints:
        subs.append(subscription)
        _save_subscriptions(subs)

    return {"success": True, "total_subscriptions": len(subs)}


async def _unsubscribe(request: Request) -> dict[str, Any]:
    """DELETE /push/unsubscribe — remove push subscription."""
    body = await request.json()
    endpoint = body.get("endpoint", "")
    if not endpoint:
        return {"success": False, "error": "endpoint required"}

    subs = _load_subscriptions()
    subs = [s for s in subs if s.get("endpoint") != endpoint]
    _save_subscriptions(subs)
    return {"success": True}


async def _test_push(request: Request) -> dict[str, Any]:
    """POST /push/test — send a test notification to all subscriptions."""
    result = send_push_notification(
        title="UMH Test",
        body="Push notifications are working.",
        category="info",
    )
    return {"success": result, "available": _PYWEBPUSH_AVAILABLE}


# ── Public API ────────────────────────────────────────────────────


def send_push_notification(
    title: str,
    body: str,
    category: str = "info",
    url: str = "/",
    data: dict[str, Any] | None = None,
) -> bool:
    """Send a push notification to all stored subscriptions.

    Categories: action_required, system_alert, info
    Returns True if at least one notification was sent successfully.
    """
    if not _PYWEBPUSH_AVAILABLE:
        logger.debug("pywebpush not available — skipping push notification")
        return False

    private_key = os.environ.get("VAPID_PRIVATE_KEY", "")
    claims_email = os.environ.get("VAPID_CLAIMS_EMAIL", "")
    if not private_key:
        logger.debug("VAPID_PRIVATE_KEY not set — skipping push notification")
        return False

    payload = json.dumps(
        {
            "title": title,
            "body": body,
            "category": category,
            "url": url,
            "data": data or {},
        }
    )

    subs = _load_subscriptions()
    if not subs:
        return False

    success_count = 0
    dead_endpoints: list[str] = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=private_key,
                vapid_claims={"sub": f"mailto:{claims_email}"},
            )
            success_count += 1
        except WebPushException as exc:
            status = getattr(exc, "response", None)
            status_code = getattr(status, "status_code", 0) if status else 0
            if status_code in (404, 410):
                dead_endpoints.append(sub.get("endpoint", ""))
                logger.debug("Removing dead push subscription: %s", sub.get("endpoint", "")[:50])
            else:
                logger.debug("Push notification failed: %s", exc)
        except Exception as exc:
            logger.debug("Push notification error: %s", exc)

    if dead_endpoints:
        subs = [s for s in subs if s.get("endpoint") not in dead_endpoints]
        _save_subscriptions(subs)

    return success_count > 0
