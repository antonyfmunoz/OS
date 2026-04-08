"""Append-only JSONL loggers for execution and decision records.

Two logs, two directories, one record per line. Simple to `tail -f`,
simple to grep, simple to replay.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from .actions import Action

EXECUTION_LOG_DIR = "/opt/OS/logs/execution"
DECISION_LOG_DIR = "/opt/OS/logs/decisions"


def _today_path(directory: str, stem: str) -> str:
    os.makedirs(directory, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return os.path.join(directory, f"{day}-{stem}.jsonl")


def _append_jsonl(path: str, record: dict[str, Any]) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def log_execution(action: Action, result: dict[str, Any] | None = None) -> str:
    """Append a full action record to today's execution log.

    Returns the path written. `result` is optional — if omitted we use
    whatever is on the action. This lets callers log at any lifecycle
    transition (proposed, rejected, failed, executed) with one call.
    """
    path = _today_path(EXECUTION_LOG_DIR, "execution")
    record = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "action": action.to_dict(),
        "result": result if result is not None else action.result,
    }
    _append_jsonl(path, record)
    return path


def log_decision(
    context: str,
    options_considered: list[str],
    chosen_option: str,
    reasoning: str,
    *,
    related_action_id: str | None = None,
    source_agent: str = "unknown",
) -> dict[str, Any]:
    """Append a decision record capturing WHY an action was (or was not) taken."""
    record = {
        "decision_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_agent": source_agent,
        "context": context,
        "options_considered": list(options_considered),
        "chosen_option": chosen_option,
        "reasoning": reasoning,
        "related_action_id": related_action_id,
    }
    path = _today_path(DECISION_LOG_DIR, "decisions")
    _append_jsonl(path, record)
    record["_log_path"] = path
    return record
