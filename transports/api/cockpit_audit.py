"""Cockpit audit event emitter — settings + unified mutation audit trail.

Settings mutations append to data/umh/settings/audit.jsonl.
All other mutations append to data/umh/audit/mutation_ledger.jsonl.

UMH transport layer.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from substrate.state.runtime_paths import runtime_state_path

logger = logging.getLogger(__name__)

_AUDIT_PATH = str(runtime_state_path("audit/settings", "audit.jsonl", create_parent=False))
_MUTATION_LEDGER_PATH = str(
    runtime_state_path("audit", "mutation_ledger.jsonl", create_parent=False)
)


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


def emit_mutation_audit(
    domain: str,
    action: str,
    target: str,
    *,
    actor: str = "operator",
    surface: str = "cockpit",
    old_value: Any = None,
    new_value: Any = None,
    persisted: bool = True,
    constraint_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Emit a mutation audit event to the unified ledger.

    Writes to data/umh/audit/mutation_ledger.jsonl using file-level
    locking (fcntl.flock) for safe concurrent appends.

    Returns the event dict so callers can include it in responses.
    """
    event: dict[str, Any] = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,
        "domain": domain,
        "surface": surface,
        "action": action,
        "target": target,
        "old_value": old_value,
        "new_value": new_value,
        "persisted": persisted,
        "constraint_warnings": constraint_warnings or [],
    }

    try:
        os.makedirs(os.path.dirname(_MUTATION_LEDGER_PATH), exist_ok=True)
        with open(_MUTATION_LEDGER_PATH, "a") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event, default=str) + "\n")
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        logger.error("Failed to write mutation audit event: %s", exc)

    logger.info("MutationAudit: %s %s.%s", action, domain, target)
    return event
