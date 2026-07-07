#!/usr/bin/env python3
"""P4S-31B proof harness — operator submit + decide through the ROUTE HANDLERS.

Runs the intent-loop input surface in-process the way FastAPI would (minus the
network): registers the real route handlers via a capturing fake router, then

  1. POST /intent-loop/submit  — captures a real generic intent → held gate,
  2. reads the surface — shows the gate HELD (AWAITING_APPROVAL, no proof),
  3. POST /intent-loop/{loop_id}/decision (approve) — governed decision,
  4. reads the surface — shows PROOF_RECORDED with the real proof record.

All ids in the output are REAL (produced by the run). No fabricated ids, no
poking the store directly. Writes a JSON proof under data/audits/proof/ and a
markdown proof under docs/audits/.
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
    submit = router.post_routes["/intent-loop/submit"]
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    read = router.get_routes["/intent-loop"]

    intent_text = "Draft a follow-up plan for the demo pipeline"

    # 1. Submit through the ROUTE HANDLER.
    submitted = submit(payload={"text": intent_text}, operator_identity="umh_operator")
    loop_id = submitted.get("loop_id")

    # 2. Read — gate HELD.
    held_surface = read()
    held_loop = next((lp for lp in held_surface["loops"] if lp["loop_id"] == loop_id), None)
    gate_held = (
        submitted.get("submitted") is True
        and submitted.get("stage") == "awaiting_approval"
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
        "surface": "intent_loop input surface (submit + decide)",
        "generated": date.today().isoformat(),
        "store_path": store_path,
        "step_1_submit_response": submitted,
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
            "submit_captured_real_loop": bool(loop_id),
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
        result["assertions"]["submit_captured_real_loop"]
        and result["assertions"]["gate_held_at_awaiting_approval"]
        and result["assertions"]["decision_reached_proof_recorded"]
        and result["assertions"]["proof_governed_success"]
    )

    print(json.dumps(result["assertions"], indent=2))
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
