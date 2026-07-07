"""P4S-31B — Cockpit intent-loop input surface (operator submit + decide).

Proves the packet's required behavior and hard constraints:

1. The submission mutation (intent_loop_submit) is registered in the REAL
   MutationRegistry and is degraded-safe (low-risk, LOCAL_FILE) so the capture
   write stays governed even with the daemon down.
2. Submit → AWAITING_APPROVAL (the gate HOLDS): no proof, no auto-advance.
3. The capture WRITE routes through the governed runner (no ungoverned append):
   a fake runner captures the exact mutation_name; nothing persists if the
   governed gate rejects.
4. The route wrappers never raise: an env-broken loop yields a stable dict, not
   a 500, for both /submit and /{loop_id}/decision.
5. The decision through the governed path reaches proof_recorded.
6. The read surface reflects the submitted loop.
"""

from __future__ import annotations

import os
import sys
import tempfile

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from substrate.execution.intent.intent_spec import IntentLoopStage
from substrate.execution.intent.loop import (
    APPROVAL_MUTATION_NAME,
    SUBMIT_MUTATION_NAME,
    IntentLoop,
    IntentLoopStore,
)
from substrate.organism.mutation_registry import MutationRegistry

_BOUNDED_INTENT = "Draft follow-up plan for demo lead pipeline"


def _fresh_loop(tmp_path: str, mutation_runner=None) -> IntentLoop:
    store = IntentLoopStore(store_path=os.path.join(tmp_path, "loops.jsonl"))
    return IntentLoop(store=store, mutation_runner=mutation_runner)


# ── 1. Submission mutation is registered in the REAL registry ─────────────────


def test_submit_mutation_is_registered():
    """Regression (#197 style): intent_loop_submit exists in the real registry."""
    reg = MutationRegistry()
    assert reg.is_registered(SUBMIT_MUTATION_NAME)


def test_submit_spec_is_degraded_safe_and_local():
    reg = MutationRegistry()
    spec = reg.lookup(SUBMIT_MUTATION_NAME)
    assert spec is not None
    assert spec.risk_level == "low"
    assert spec.blast_radius.value in ("local_file", "local_runtime")
    assert spec.degraded_mode_allowed is True


# ── 2. Submit holds the gate ──────────────────────────────────────────────────


def test_submit_holds_at_approval_gate():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value
        assert rec.proof is None
        # Persisted and still held — no auto-advance past the gate.
        stored = loop._store.get(rec.loop_id)
        assert stored is not None
        assert stored.stage == IntentLoopStage.AWAITING_APPROVAL.value


# ── 3. Governed capture (no ungoverned append) ────────────────────────────────


def test_submit_routes_through_governed_runner():
    """The capture must submit exactly the registered submit mutation name to the
    governed runner — proving no ungoverned append, at runtime."""
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        output, success = kwargs["execute_fn"]()

        class _Resp:
            def __init__(self):
                self.success = success
                self.output = output
                self.envelope_id = "env_submit_123"
                self.status = "completed"
                self.degraded = False

        return _Resp()

    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp, mutation_runner=fake_runner)
        rec = loop.submit(_BOUNDED_INTENT)

    assert captured["mutation_name"] == SUBMIT_MUTATION_NAME
    assert callable(captured["execute_fn"])
    assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value


def test_submit_fails_closed_when_governance_rejects():
    """If the governed gate rejects the capture, nothing persists and submit
    surfaces the rejection rather than a phantom loop."""

    def rejecting_runner(**kwargs):
        # Emulate the fail-closed gate: never runs execute_fn, returns not-success.
        class _Resp:
            success = False
            output = "rejected (fail-closed)"
            envelope_id = ""
            status = "rejected_control_plane_unavailable"
            degraded = True
            rejected_reason = "not eligible"

        return _Resp()

    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp, mutation_runner=rejecting_runner)
        raised = False
        try:
            loop.submit(_BOUNDED_INTENT)
        except RuntimeError:
            raised = True
        assert raised, "submit must fail closed when governance rejects the capture"
        # Nothing persisted.
        assert loop._store.load_all() == []


def test_real_governed_submit_end_to_end():
    """With no injected runner, submit resolves the substrate-native governed
    gate; the submit spec is degraded-safe so the capture executes (governed),
    landing the loop at AWAITING_APPROVAL — never ungoverned."""
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)  # no runner → real route_mutation_degraded
        rec = loop.submit(_BOUNDED_INTENT)
    assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value


# ── 4. Route wrappers never raise ─────────────────────────────────────────────


class _FakeRouter:
    """Captures route handlers registered via the decorator, so we can call them
    in-process exactly as FastAPI would (minus the network)."""

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


def _register_routes():
    from transports.api.cockpit_intent_loop_routes import register_intent_loop_routes

    router = _FakeRouter()

    def _require_operator_role():
        return "umh_operator"

    register_intent_loop_routes(router, _require_operator_role, {})
    return router


def test_submit_route_never_raises_on_empty_text():
    router = _register_routes()
    submit = router.post_routes["/intent-loop/submit"]
    out = submit(payload={}, operator_identity="umh_operator")
    assert isinstance(out, dict)
    assert out["submitted"] is False
    assert out["error"]


def test_decision_route_never_raises_on_unknown_loop():
    router = _register_routes()
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    out = decide(
        loop_id="loop_does_not_exist",
        payload={"decision": "approve"},
        operator_identity="umh_operator",
    )
    assert isinstance(out, dict)
    assert out["decided"] is False
    assert out["error"]


def test_submit_and_decide_routes_reach_proof_recorded(tmp_path, monkeypatch):
    """End-to-end through the ROUTE HANDLER functions (not the store directly):
    submit → held → decide(approve) → proof_recorded, and the read surface
    reflects it. Uses an isolated store path so the assertion is on a real,
    freshly-submitted loop."""
    store_path = os.path.join(tmp_path, "route_loops.jsonl")
    monkeypatch.setenv("UMH_ROOT", str(tmp_path))
    # Point the default store at the isolated path via env-derived default.
    import substrate.execution.intent.loop as loop_mod

    monkeypatch.setattr(loop_mod, "_DEFAULT_STORE_PATH", store_path)

    router = _register_routes()
    submit = router.post_routes["/intent-loop/submit"]
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    read = router.get_routes["/intent-loop"]

    submitted = submit(payload={"text": _BOUNDED_INTENT}, operator_identity="umh_operator")
    assert submitted["submitted"] is True
    loop_id = submitted["loop_id"]
    assert submitted["stage"] == IntentLoopStage.AWAITING_APPROVAL.value

    # Read surface reflects the held loop.
    surface = read()
    assert any(lp["loop_id"] == loop_id for lp in surface["loops"])
    held = next(lp for lp in surface["loops"] if lp["loop_id"] == loop_id)
    assert held["stage"] == IntentLoopStage.AWAITING_APPROVAL.value

    decided = decide(
        loop_id=loop_id, payload={"decision": "approve"}, operator_identity="umh_operator"
    )
    assert decided["decided"] is True
    assert decided["stage"] == IntentLoopStage.PROOF_RECORDED.value
    assert decided["proof"]["mutation_name"] == APPROVAL_MUTATION_NAME
    assert decided["proof"]["governed_success"] is True

    # Read surface reflects the proof.
    surface2 = read()
    proven = next(lp for lp in surface2["loops"] if lp["loop_id"] == loop_id)
    assert proven["stage"] == IntentLoopStage.PROOF_RECORDED.value
    assert proven["proof"] is not None
