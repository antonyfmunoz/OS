"""Cockpit audit event emitter — settings mutation audit trail.

Appends structured events to data/umh/settings/audit.jsonl.
Every settings mutation (model routing, governance, device) emits an event.

UMH transport layer.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_ROOT = os.environ.get("UMH_ROOT") or "/opt/OS"
_AUDIT_PATH = os.path.join(_ROOT, "data", "umh", "settings", "audit.jsonl")


def emit_settings_audit(
    action: str,
    target: str,
    old_value: Any,
    new_value: Any,
    domain: str,
    surface: str = "cockpit_settings",
    persisted: bool = True,
    constraint_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Emit and persist a settings audit event. Returns the event dict."""
    event = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": "operator",
        "surface": surface,
        "action": action,
        "target": target,
        "domain": domain,
        "old_value": old_value,
        "new_value": new_value,
        "persisted": persisted,
        "constraint_warnings": constraint_warnings or [],
    }

    try:
        os.makedirs(os.path.dirname(_AUDIT_PATH), exist_ok=True)
        with open(_AUDIT_PATH, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError as exc:
        logger.error("Failed to write audit event: %s", exc)

    logger.info("Audit: %s %s.%s", action, domain, target)
    return event
