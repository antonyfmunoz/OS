"""Approval queue — operator approval/rejection of governance-blocked actions.

Wraps the substrate ApprovalStore for the workstation CLI. Provides
show_pending(), approve_item(), reject_item() for the interaction loop,
plus pending_count() for the status display.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_store() -> Any:
    """Lazy-load the substrate ApprovalStore."""
    try:
        from substrate.organism.approval_store import ApprovalStore

        return ApprovalStore()
    except ImportError:
        logger.debug("ApprovalStore not available")
        return None


def pending_count() -> int:
    """Get count of pending approvals."""
    store = _get_store()
    if store is None:
        return 0
    try:
        return store.pending_count()
    except Exception as exc:
        logger.debug("Failed to get pending approval count: %s", exc)
        return 0


def show_pending() -> str:
    """Format pending approvals for display."""
    store = _get_store()
    if store is None:
        return "Approval store not available."

    try:
        pending = store.list_approvals(status="pending")
    except Exception as exc:
        return f"Failed to load approvals: {exc}"

    if not pending:
        return "No pending approvals."

    lines = [f"{len(pending)} pending approval(s):", ""]
    for item in pending:
        aid = item.get("id", "?")[:8]
        title = item.get("title", "untitled")
        agent = item.get("agent", "?")
        risk = item.get("risk_level", "?")
        created = item.get("created_at", "?")
        if isinstance(created, str) and len(created) > 19:
            created = created[:19]
        lines.append(f"  [{aid}] {title}")
        lines.append(f"         agent={agent}  risk={risk}  created={created}")
        rationale = item.get("governance_rationale", "")
        if rationale:
            lines.append(f"         rationale: {rationale[:80]}")
        lines.append("")

    lines.append("Use 'approve <id>' or 'reject <id>' to decide.")
    return "\n".join(lines)


def approve_item(approval_id: str) -> str:
    """Approve a pending item by ID (prefix match)."""
    store = _get_store()
    if store is None:
        return "Approval store not available."

    full_id = _resolve_id(store, approval_id)
    if full_id is None:
        return f"No pending approval matching '{approval_id}'."
    if full_id.startswith("__AMBIGUOUS__"):
        count = full_id.split("__")[-1]
        return f"Ambiguous — '{approval_id}' matches {count} items. Use a longer prefix."

    try:
        result = store.decide(full_id, "approved", decided_by="operator")
        if result is None:
            return f"Approval '{approval_id}' not found."
        return f"Approved: {result.get('title', approval_id)}"
    except Exception as exc:
        return f"Approval failed: {exc}"


def reject_item(approval_id: str) -> str:
    """Reject a pending item by ID (prefix match)."""
    store = _get_store()
    if store is None:
        return "Approval store not available."

    full_id = _resolve_id(store, approval_id)
    if full_id is None:
        return f"No pending approval matching '{approval_id}'."
    if full_id.startswith("__AMBIGUOUS__"):
        count = full_id.split("__")[-1]
        return f"Ambiguous — '{approval_id}' matches {count} items. Use a longer prefix."

    try:
        result = store.decide(full_id, "rejected", decided_by="operator")
        if result is None:
            return f"Approval '{approval_id}' not found."
        return f"Rejected: {result.get('title', approval_id)}"
    except Exception as exc:
        return f"Rejection failed: {exc}"


def _resolve_id(store: Any, partial: str) -> str | None:
    """Resolve a partial ID to a full approval ID.

    Returns None if no match or if the prefix is ambiguous (multiple matches).
    """
    try:
        pending = store.list_approvals(status="pending")
    except Exception as exc:
        logger.debug("Failed to list approvals: %s", exc)
        return None

    partial = partial.strip().lower()
    matches = [
        item.get("id", "") for item in pending if item.get("id", "").lower().startswith(partial)
    ]

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        logger.warning("Ambiguous approval ID prefix %r — matches %d items", partial, len(matches))
        return f"__AMBIGUOUS__{len(matches)}"
    return None


def show_approvals() -> int:
    """Display approval queue for CLI."""
    print()
    print("Approval Queue")
    print("=" * 40)
    print(show_pending())
    print()
    return 0
