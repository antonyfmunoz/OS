"""Operator state sync — bridge workstation modes to substrate OperatorState.

Synchronizes the workstation's SystemMode (ACTIVE/AWAY) with the
substrate's OperatorMode (IDLE/STARTING/ACTIVE/FOCUSED/CLOSING/UNAVAILABLE).

The workstation drives transitions through well-defined trigger points:
  - Boot: IDLE -> STARTING -> ACTIVE
  - Perception away: ACTIVE -> IDLE
  - Perception return: IDLE -> ACTIVE
  - Exit: ACTIVE -> CLOSING -> IDLE
  - Voice session start/end: updates voice session fields

Uses the substrate's apply_* helpers from operator_transitions.py
which handle all transition logic and persistence.

UMH workstation subsystem.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_NODE_ID = "workstation_local"


def _get_store() -> Any:
    """Lazy-load the OperatorStateStore."""
    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        return get_operator_state_store()
    except ImportError:
        logger.debug("OperatorStateStore not available")
        return None


def _get_state(node_id: str = _NODE_ID) -> Any:
    """Get or create the OperatorState for this node."""
    store = _get_store()
    if store is None:
        return None
    try:
        return store.get_or_create(node_id)
    except Exception as exc:
        logger.debug("Failed to get operator state: %s", exc)
        return None


def sync_boot(node_id: str = _NODE_ID) -> dict[str, Any]:
    """Sync operator state on workstation boot — transition to ACTIVE."""
    try:
        from substrate.execution.bridge.operator_state import (
            OperatorMode,
            OperatorTransition,
            get_operator_state_store,
        )

        store = get_operator_state_store()
        state = store.get_or_create(node_id)

        if state.mode != OperatorMode.ACTIVE:
            from datetime import datetime
            from uuid import uuid4

            transition = OperatorTransition(
                transition_id=f"ot_{uuid4().hex[:12]}",
                node_id=node_id,
                from_mode=state.mode.value,
                to_mode=OperatorMode.ACTIVE.value,
                trigger="workstation_boot",
                reason="workstation booted — operator present",
                occurred_at=datetime.now(datetime.UTC).isoformat(),
            )
            state.append_transition(transition)
            state.mode = OperatorMode.ACTIVE
            store.put(state)

        return {
            "status": "synced",
            "mode": state.mode.value,
            "node_id": node_id,
        }
    except ImportError:
        return {"status": "skipped", "reason": "substrate_unavailable"}
    except Exception as exc:
        logger.debug("Boot sync failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


def sync_away(node_id: str = _NODE_ID) -> dict[str, Any]:
    """Sync operator state when perception detects operator away."""
    try:
        from substrate.execution.bridge.operator_state import (
            OperatorMode,
            OperatorTransition,
            get_operator_state_store,
        )

        store = get_operator_state_store()
        state = store.get_or_create(node_id)

        if state.mode in (OperatorMode.ACTIVE, OperatorMode.FOCUSED):
            from datetime import datetime
            from uuid import uuid4

            transition = OperatorTransition(
                transition_id=f"ot_{uuid4().hex[:12]}",
                node_id=node_id,
                from_mode=state.mode.value,
                to_mode=OperatorMode.IDLE.value,
                trigger="perception_away",
                reason="operator left workstation (perception timeout)",
                occurred_at=datetime.now(datetime.UTC).isoformat(),
            )
            state.append_transition(transition)
            state.mode = OperatorMode.IDLE
            state.active_voice_session_id = None
            state.active_voice_role = None
            store.put(state)

        return {"status": "synced", "mode": state.mode.value}
    except ImportError:
        return {"status": "skipped", "reason": "substrate_unavailable"}
    except Exception as exc:
        logger.debug("Away sync failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


def sync_return(node_id: str = _NODE_ID) -> dict[str, Any]:
    """Sync operator state when perception detects operator returned."""
    try:
        from substrate.execution.bridge.operator_state import (
            OperatorMode,
            OperatorTransition,
            get_operator_state_store,
        )

        store = get_operator_state_store()
        state = store.get_or_create(node_id)

        if state.mode in (OperatorMode.IDLE, OperatorMode.UNAVAILABLE):
            from datetime import datetime
            from uuid import uuid4

            transition = OperatorTransition(
                transition_id=f"ot_{uuid4().hex[:12]}",
                node_id=node_id,
                from_mode=state.mode.value,
                to_mode=OperatorMode.ACTIVE.value,
                trigger="perception_return",
                reason="operator returned to workstation",
                occurred_at=datetime.now(datetime.UTC).isoformat(),
            )
            state.append_transition(transition)
            state.mode = OperatorMode.ACTIVE
            store.put(state)

        return {"status": "synced", "mode": state.mode.value}
    except ImportError:
        return {"status": "skipped", "reason": "substrate_unavailable"}
    except Exception as exc:
        logger.debug("Return sync failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


def sync_exit(node_id: str = _NODE_ID) -> dict[str, Any]:
    """Sync operator state on workstation exit — transition through CLOSING to IDLE."""
    try:
        from datetime import datetime
        from uuid import uuid4

        from substrate.execution.bridge.operator_state import (
            OperatorMode,
            OperatorTransition,
            get_operator_state_store,
        )

        store = get_operator_state_store()
        state = store.get_or_create(node_id)

        now = datetime.now(datetime.UTC).isoformat()

        if state.mode != OperatorMode.IDLE:
            closing_transition = OperatorTransition(
                transition_id=f"ot_{uuid4().hex[:12]}",
                node_id=node_id,
                from_mode=state.mode.value,
                to_mode=OperatorMode.CLOSING.value,
                trigger="workstation_exit",
                reason="workstation shutting down",
                occurred_at=now,
            )
            state.append_transition(closing_transition)
            state.mode = OperatorMode.CLOSING

            idle_transition = OperatorTransition(
                transition_id=f"ot_{uuid4().hex[:12]}",
                node_id=node_id,
                from_mode=OperatorMode.CLOSING.value,
                to_mode=OperatorMode.IDLE.value,
                trigger="workstation_exit_complete",
                reason="workstation shutdown complete",
                occurred_at=now,
            )
            state.append_transition(idle_transition)
            state.mode = OperatorMode.IDLE

        state.active_voice_session_id = None
        state.active_voice_role = None
        store.put(state)

        return {"status": "synced", "mode": state.mode.value}
    except ImportError:
        return {"status": "skipped", "reason": "substrate_unavailable"}
    except Exception as exc:
        logger.debug("Exit sync failed: %s", exc)
        return {"status": "error", "reason": str(exc)}


def get_operator_status(node_id: str = _NODE_ID) -> dict[str, Any]:
    """Get current operator state for display."""
    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        store = get_operator_state_store()
        state = store.get(node_id)
        if state is None:
            return {"mode": "unknown", "node_id": node_id}

        result: dict[str, Any] = {
            "mode": state.mode.value,
            "is_active": state.is_active,
            "node_id": node_id,
        }

        if state.active_voice_session_id:
            result["voice_session"] = state.active_voice_session_id[:12]
        if state.active_voice_role:
            result["voice_role"] = state.active_voice_role
        if state.last_wake_kind:
            result["last_wake"] = state.last_wake_kind
        if state.current_ritual_kind:
            result["ritual"] = f"{state.current_ritual_kind} ({state.current_ritual_state})"
        if state.readiness_classification:
            result["readiness"] = state.readiness_classification

        last = state.last_transition
        if last is not None:
            result["last_transition"] = {
                "from": last.from_mode,
                "to": last.to_mode,
                "trigger": last.trigger,
                "at": last.occurred_at[:19] if len(last.occurred_at) > 19 else last.occurred_at,
            }

        return result
    except ImportError:
        return {"mode": "unavailable", "reason": "substrate not available"}
    except Exception as exc:
        return {"mode": "error", "reason": str(exc)}


def show_operator_state(node_id: str = _NODE_ID) -> int:
    """Display operator state for CLI."""
    print()
    print("Operator State")
    print("=" * 40)

    status = get_operator_status(node_id)
    mode = status.get("mode", "?")
    active = status.get("is_active", False)
    print(f"  Mode:      {mode} ({'active' if active else 'inactive'})")
    print(f"  Node:      {status.get('node_id', '?')}")

    if "voice_session" in status:
        print(f"  Voice:     {status['voice_session']} (role: {status.get('voice_role', '?')})")
    if "last_wake" in status:
        print(f"  Last wake: {status['last_wake']}")
    if "ritual" in status:
        print(f"  Ritual:    {status['ritual']}")
    if "readiness" in status:
        print(f"  Readiness: {status['readiness']}")

    last = status.get("last_transition")
    if last:
        print("\n  Last transition:")
        print(f"    {last.get('from', '?')} -> {last.get('to', '?')}")
        print(f"    trigger: {last.get('trigger', '?')}")
        print(f"    at: {last.get('at', '?')}")

    try:
        from substrate.execution.bridge.operator_state import get_operator_state_store

        store = get_operator_state_store()
        state = store.get(node_id)
        if state and state.transitions:
            print(f"\n  Recent transitions ({len(state.transitions)}):")
            for t in state.transitions[-5:]:
                at = t.occurred_at[:19] if len(t.occurred_at) > 19 else t.occurred_at
                print(f"    [{t.trigger}] {t.from_mode} -> {t.to_mode} at {at}")
    except Exception as exc:
        logger.debug("Transition history display failed: %s", exc)

    print()
    return 0
