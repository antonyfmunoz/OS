"""Cockpit intent-loop route — P4S-31 MVP operating-loop read surface.

Covers: GET /intent-loop. Thin transport wrapper over the substrate-owned
accessor (substrate.execution.intent.loop::read_intent_loop_surface), following
the read-surface discipline of rules/projection-read-surfaces.md adapted for a
substrate-owned surface:

- lazy import of the accessor INSIDE the handler,
- body is: import accessor → call it → return it (no reshaping),
- try/except → dict, never a 500,
- operator-only auth like sibling cockpit routes.

The path is /intent-loop (not /intent/loop) to avoid colliding with the
existing /intent/{intent_id} intent-preservation route in
cockpit_intent_routes.py — a different concern (IntentRuntime capture/lineage).

The write path (approve/reject) is intentionally NOT exposed as a raw route in
this MVP skeleton — decisions flow through the canonical governed_mutation
runtime (IntentLoop.decide), exercised in-process by the P4S-31 proof. Adding a
governed POST seam is a bounded follow-on, not part of this skeleton.

UMH transport layer.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def register_intent_loop_routes(router, _require_operator_role, helpers):
    """Register the intent-loop read surface onto the given router."""

    from fastapi import Depends

    @router.get("/intent-loop", dependencies=[Depends(_require_operator_role)])
    def intent_loop():
        """MVP operating-loop server truth — P4S-31.

        Reflects the substrate-owned intent-loop state: each captured intent, its
        drafted packet, the held/decided approval gate, and any governed proof
        record. Read-only mirror; never mutates. Returns a stable flat dict on
        every path (never a 500).
        """
        try:
            from substrate.execution.intent.loop import read_intent_loop_surface

            return read_intent_loop_surface()
        except Exception as e:
            logger.debug("intent loop read surface failed: %s", e)
            return {
                "surface": "intent_loop",
                "connection_status": "error",
                "total": 0,
                "awaiting_approval": 0,
                "proof_recorded": 0,
                "stage_counts": {},
                "loops": [],
                "error": str(e),
            }
