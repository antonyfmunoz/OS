#!/usr/bin/env python3
"""P4S-31B proof harness — Cockpit Chat intent rail, through the REAL handlers.

Doctrine: intent originates ONLY through sanctioned Cockpit conversational
surfaces. This proof drives the full chain in-process through the ACTUAL
handler functions (the real /advisor/converse endpoint from the real chat
router, and the real intent-loop route handlers) — no store poking, no
fabricated ids:

  chat_submit → intent_loop → awaiting_approval → governed_approve → proof_recorded

  1. POST /advisor/converse with an intent-bearing chat message → the
     deterministic rail (classify_intent, no LLM) captures it via the governed
     intent_loop_submit mutation; server-truth status returns into the SAME
     chat thread (ChatResponse dict),
  2. GET /intent-loop — gate HELD (AWAITING_APPROVAL, no proof),
  3. POST /intent-loop/{loop_id}/decision (approve) — governed decision,
  4. GET /intent-loop — PROOF_RECORDED with the real proof record.

Writes a JSON proof under data/audits/proof/ and prints the assertion summary.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

# Deterministically classifies as CommandIntent.INTENT_CAPTURE ("fix this").
_CHAT_INTENT = "Fix this bug in the demo pipeline dashboard"


class _FakeRouter:
    def __init__(self):
        self.get_routes: dict[str, object] = {}
        self.post_routes: dict[str, object] = {}

    def get(self, path, **_kwargs):
        def _register(fn):
            self.get_routes[path] = fn
            return fn

        return _register

    def post(self, path, **_kwargs):
        def _register(fn):
            self.post_routes[path] = fn
            return fn

        return _register


def _real_advisor_converse():
    """Build the REAL chat router (as cockpit.py does; organism state truthful
    to this environment) and return the actual /advisor/converse endpoint."""
    import transports.api.cockpit_chat_routes as chat_mod

    chat_mod.configure(
        get_organism_fn=lambda: None,  # daemon down in this env — truthful
        push_chat_message_fn=lambda msg: None,
        require_operator_dep=lambda: "umh_operator",
    )
    for route in chat_mod.chat_router.routes:
        if getattr(route, "path", "") == "/advisor/converse":
            return route.endpoint
    raise AssertionError("/advisor/converse route not found")


def main() -> int:
    # Isolated substrate-owned store so the proof reads a clean, real surface.
    tmp = tempfile.mkdtemp(prefix="p4s31b_proof_")
    store_path = os.path.join(tmp, "intent_loops.jsonl")
    import substrate.execution.intent.loop as loop_mod

    loop_mod._DEFAULT_STORE_PATH = store_path

    from transports.api.cockpit_intent_loop_routes import register_intent_loop_routes

    router = _FakeRouter()

    def _require_operator_role():
        return "umh_operator"

    register_intent_loop_routes(router, _require_operator_role, {})
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    read = router.get_routes["/intent-loop"]

    advisor_converse = _real_advisor_converse()

    # 1. Chat submit through the REAL /advisor/converse handler.
    chat_response = advisor_converse({"content": _CHAT_INTENT})
    meta = chat_response.get("metadata", {}) if isinstance(chat_response, dict) else {}
    loop_id = meta.get("loop_id")

    # 2. Read — gate HELD.
    held_surface = read()
    held_loop = next((lp for lp in held_surface["loops"] if lp["loop_id"] == loop_id), None)
    gate_held = (
        meta.get("submitted") is True
        and chat_response.get("intent") == "intent_loop_submit"
        and meta.get("stage") == "awaiting_approval"
        and held_loop is not None
        and held_loop["stage"] == "awaiting_approval"
        and held_loop["proof"] is None
    )

    # 3. Decide (approve) through the ROUTE HANDLER — governed.
    decided = decide(
        loop_id=loop_id,
        payload={"decision": "approve"},
        operator_identity="umh_operator",
    )

    # 4. Read — PROOF_RECORDED.
    proof_surface = read()
    proven_loop = next((lp for lp in proof_surface["loops"] if lp["loop_id"] == loop_id), None)
    proof_recorded = (
        decided.get("decided") is True
        and decided.get("stage") == "proof_recorded"
        and proven_loop is not None
        and proven_loop["stage"] == "proof_recorded"
        and proven_loop["proof"] is not None
    )

    result = {
        "packet": "P4S-31B",
        "surface": "Cockpit Chat intent rail (chat submit + governed decide)",
        "chain": (
            "chat_submit -> intent_loop -> awaiting_approval -> governed_approve -> proof_recorded"
        ),
        "generated": date.today().isoformat(),
        "store_path": store_path,
        "step_1_chat_message": _CHAT_INTENT,
        "step_1_chat_thread_response": chat_response,
        "step_2_gate_held": {
            "gate_held": gate_held,
            "held_loop": held_loop,
        },
        "step_3_decision_response": decided,
        "step_4_proof_recorded": {
            "proof_recorded": proof_recorded,
            "proven_loop": proven_loop,
        },
        "assertions": {
            "chat_rail_captured_real_loop": bool(loop_id),
            "chat_thread_received_server_truth_status": bool(
                isinstance(chat_response, dict) and chat_response.get("text")
            ),
            "gate_held_at_awaiting_approval": gate_held,
            "decision_reached_proof_recorded": proof_recorded,
            "proof_governed_success": bool(
                proven_loop and proven_loop["proof"] and proven_loop["proof"]["governed_success"]
            ),
            "proof_mutation_name": (
                proven_loop["proof"]["mutation_name"]
                if proven_loop and proven_loop["proof"]
                else None
            ),
        },
    }

    json_path = os.path.join(
        _WORKTREE,
        "data",
        "audits",
        "proof",
        f"{date.today().isoformat()}_p4s31b_input_surface_proof.json",
    )
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    ok = (
        result["assertions"]["chat_rail_captured_real_loop"]
        and result["assertions"]["chat_thread_received_server_truth_status"]
        and result["assertions"]["gate_held_at_awaiting_approval"]
        and result["assertions"]["decision_reached_proof_recorded"]
        and result["assertions"]["proof_governed_success"]
    )

    print(json.dumps(result["assertions"], indent=2))
    print(f"\nchat message: {_CHAT_INTENT}")
    print(f"chat thread status: {chat_response.get('text', '')}")
    print(f"\nloop_id: {loop_id}")
    if proven_loop and proven_loop["proof"]:
        p = proven_loop["proof"]
        print(f"proof_id: {p['proof_id']}")
        print(f"envelope_id: {p['envelope_id']}")
        print(f"governance_status: {p['governance_status']}")
        print(f"degraded: {p['degraded']}")
    print(f"\nJSON proof: {json_path}")
    print(f"PROOF {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
