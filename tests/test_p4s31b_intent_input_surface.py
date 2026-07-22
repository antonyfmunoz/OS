"""P4S-31B — Cockpit Chat intent rail (governed submit + decide).

Doctrine (architecture correction): intent originates ONLY through sanctioned
Cockpit conversational surfaces — Cockpit Chat now, Cockpit Voice later as a
thin adapter into the same Chat channel. Panels are downstream control surfaces
only (approve/reject/inspect); no panel-side submit path may exist.

Proves the packet's required behavior and hard constraints:

1. The submission mutation (intent_loop_submit) is registered in the REAL
   MutationRegistry and is degraded-safe (low-risk, LOCAL_FILE) so the capture
   write stays governed even with the daemon down.
2. Submit → AWAITING_APPROVAL (the gate HOLDS): no proof, no auto-advance.
3. The capture WRITE routes through the governed runner (no ungoverned append):
   a fake runner captures the exact mutation_name; nothing persists if the
   governed gate rejects.
4. The CHAT RAIL: an intent-bearing Cockpit Chat message (deterministic
   classify_intent — keyword table, no LLM) produces the canonical intent event
   with the same held-gate semantics; conversational text passes through to the
   normal chat path. The rail runs in the real /advisor/converse handler.
5. NO PANEL BYPASS: the cockpit panel/store have no submit path — intent enters
   only through the chat rail (or the canonical POST /intent-loop/submit
   endpoint the rail shares its governed submit with).
6. The route wrappers never raise: env-broken input yields a stable dict, not a
   500, for both /submit and /{loop_id}/decision.
7. The decision through the governed path reaches proof_recorded, and the read
   surface reflects the submitted loop.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

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
# Deterministically classifies as CommandIntent.INTENT_CAPTURE ("fix this").
_CHAT_INTENT = "Fix this bug in the demo pipeline dashboard"
# Deterministically does NOT classify as INTENT_CAPTURE (conversation).
_CHAT_CONVERSATION = "what do you think about our positioning"

_COCKPIT_DIR = Path(_WORKTREE) / "cockpit" / "src" / "renderer"
_PANEL_PATH = _COCKPIT_DIR / "panels" / "IntentLoopPanel.tsx"
_STORE_PATH = _COCKPIT_DIR / "stores" / "intentLoopStore.ts"
_CHAT_ROUTES_PATH = Path(_WORKTREE) / "transports" / "api" / "cockpit_chat_routes.py"


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


# ── 4. The Cockpit Chat intent rail ───────────────────────────────────────────


def _isolate_store(tmp_path, monkeypatch):
    import substrate.execution.intent.loop as loop_mod

    store_path = os.path.join(tmp_path, "rail_loops.jsonl")
    monkeypatch.setattr(loop_mod, "_DEFAULT_STORE_PATH", store_path)
    return store_path


def test_chat_rail_classification_is_deterministic():
    """The rail's trigger is the EXISTING deterministic classifier — same input,
    same classification, no LLM."""
    from substrate.workstation.command_router import CommandIntent, classify_intent

    assert classify_intent(_CHAT_INTENT) == CommandIntent.INTENT_CAPTURE
    assert classify_intent(_CHAT_INTENT) == CommandIntent.INTENT_CAPTURE  # stable
    assert classify_intent(_CHAT_CONVERSATION) != CommandIntent.INTENT_CAPTURE


def test_chat_rail_produces_canonical_intent_event(tmp_path, monkeypatch):
    """An intent-bearing chat message → canonical intent event → gate HELD at
    AWAITING_APPROVAL, with the server-truth status shaped for the SAME chat
    thread (ChatResponse dict)."""
    store_path = _isolate_store(tmp_path, monkeypatch)
    from transports.api.cockpit_chat_routes import try_chat_intent_rail

    out = try_chat_intent_rail(_CHAT_INTENT, conversation_id="conv-test123")
    assert out is not None
    # ChatResponse shape — lands in the same thread as the assistant message.
    for key in ("message_id", "text", "conversation_id", "intent", "metadata", "timestamp"):
        assert key in out
    assert out["conversation_id"] == "conv-test123"
    assert out["intent"] == "intent_loop_submit"
    meta = out["metadata"]
    assert meta["submitted"] is True
    assert meta["stage"] == IntentLoopStage.AWAITING_APPROVAL.value
    assert meta["loop_id"]

    # Held-gate semantics on the server-truth store: same as a direct submit.
    store = IntentLoopStore(store_path=store_path)
    rec = store.get(meta["loop_id"])
    assert rec is not None
    assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value
    assert rec.proof is None


def test_chat_rail_passes_conversation_through():
    """Non-intent chat returns None so the normal conversation path proceeds —
    the rail never fabricates an intent from pure chat."""
    from transports.api.cockpit_chat_routes import try_chat_intent_rail

    assert try_chat_intent_rail(_CHAT_CONVERSATION) is None


def _advisor_converse_endpoint():
    """Build the REAL chat router (organism down) and return the actual
    /advisor/converse endpoint function."""
    import transports.api.cockpit_chat_routes as chat_mod

    chat_mod.configure(
        get_organism_fn=lambda: None,
        push_chat_message_fn=lambda msg: None,
        require_operator_dep=lambda: "umh_operator",
    )
    for route in chat_mod.chat_router.routes:
        if getattr(route, "path", "") == "/advisor/converse":
            return route.endpoint
    raise AssertionError("/advisor/converse route not found")


def test_advisor_converse_routes_intent_through_rail(tmp_path, monkeypatch):
    """Through the ACTUAL chat handler: a work-bearing message is captured by
    the WAVE 1 PLANNING rail (§23.5 cutover — the canonical Operator Intent
    Protocol replaced the legacy intent-loop rail on this path), while a
    conversational message follows the normal daemon-dependent path.

    The cutover contract: new Cockpit submissions NEVER write legacy
    IntentLoopRecords. The legacy loop remains reachable ONLY via the
    explicit POST /intent-loop/submit compatibility route.
    """
    store_path = _isolate_store(tmp_path, monkeypatch)
    monkeypatch.setenv("UMH_ORG_ID", "test-org")
    monkeypatch.setenv("UMH_STATE_DIR", str(tmp_path / "state"))
    endpoint = _advisor_converse_endpoint()

    out = endpoint({"content": _CHAT_INTENT})
    # The planning rail (not the legacy loop) owns the work seam now.
    assert out["metadata"]["surface"] == "objective_plan"
    assert out["intent"] in ("create_task", "create_objective")

    # §23.5: ZERO legacy IntentLoopRecords written by the chat path.
    store = IntentLoopStore(store_path=store_path)
    assert store.load_all() == []

    # Conversational text does NOT enter any work rail; with the organism
    # down it hits the normal daemon-dependent path.
    conv_out = endpoint({"content": _CHAT_CONVERSATION})
    assert conv_out == {"error": "organism not running"}


# ── 5. No panel-side submit bypass ────────────────────────────────────────────


def test_no_panel_submit_bypass():
    """Doctrine: panels are downstream control surfaces only. Neither the panel
    nor its store may carry a submit path to the intent loop."""
    panel_src = _PANEL_PATH.read_text(encoding="utf-8")
    store_src = _STORE_PATH.read_text(encoding="utf-8")
    for src, name in ((panel_src, "IntentLoopPanel.tsx"), (store_src, "intentLoopStore.ts")):
        assert "/intent-loop/submit" not in src, (
            f"{name} must not call the submit endpoint — intent originates in Cockpit Chat"
        )
        assert "submitIntent" not in src, f"{name} must not expose a submit action"
    # The panel keeps the downstream decision control.
    assert "/intent-loop/" in store_src and "/decision" in store_src


def test_advisor_converse_wires_the_rail():
    """The real chat handler consults the rail (source-level wiring check)."""
    src = _CHAT_ROUTES_PATH.read_text(encoding="utf-8")
    assert "try_chat_intent_rail(" in src
    assert "classify_intent" in src  # deterministic trigger, no LLM
    assert "governed_intent_submit" in src  # shared governed submit


# ── 6. Route wrappers never raise ─────────────────────────────────────────────


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


# ── 7. Full rail → decision → proof through the route handlers ────────────────


def test_submit_and_decide_routes_reach_proof_recorded(tmp_path, monkeypatch):
    """End-to-end through the ROUTE HANDLER functions (not the store directly):
    submit → held → decide(approve) → proof_recorded, and the read surface
    reflects it. Uses an isolated store path so the assertion is on a real,
    freshly-submitted loop."""
    _isolate_store(tmp_path, monkeypatch)

    router = _register_routes()
    submit = router.post_routes["/intent-loop/submit"]
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    read = router.get_routes["/intent-loop"]

    submitted = submit(payload={"text": _BOUNDED_INTENT}, operator_identity="umh_operator")
    assert submitted["submitted"] is True
    loop_id = submitted["loop_id"]
    assert submitted["stage"] == IntentLoopStage.AWAITING_APPROVAL.value

    # Read surface reflects the held loop. The hardening packet
    # (P4S-31C-RUNTIME-READ-PATH-HARDENING-001) made this route async —
    # run the coroutine when calling the handler directly.
    import asyncio as _asyncio
    import inspect as _inspect

    surface = read()
    if _inspect.iscoroutine(surface):
        surface = _asyncio.run(surface)
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
    import asyncio as _asyncio2
    import inspect as _inspect2

    if _inspect2.iscoroutine(surface2):
        surface2 = _asyncio2.run(surface2)
    proven = next(lp for lp in surface2["loops"] if lp["loop_id"] == loop_id)
    assert proven["stage"] == IntentLoopStage.PROOF_RECORDED.value
    assert proven["proof"] is not None


def test_chat_rail_then_decision_reaches_proof(tmp_path, monkeypatch):
    """The doctrine chain end-to-end: chat_submit → intent_loop →
    awaiting_approval → governed_approve → proof_recorded."""
    _isolate_store(tmp_path, monkeypatch)
    from transports.api.cockpit_chat_routes import try_chat_intent_rail

    rail = try_chat_intent_rail(_CHAT_INTENT)
    assert rail is not None and rail["metadata"]["submitted"] is True
    loop_id = rail["metadata"]["loop_id"]
    assert rail["metadata"]["stage"] == IntentLoopStage.AWAITING_APPROVAL.value

    router = _register_routes()
    decide = router.post_routes["/intent-loop/{loop_id}/decision"]
    decided = decide(
        loop_id=loop_id, payload={"decision": "approve"}, operator_identity="umh_operator"
    )
    assert decided["decided"] is True
    assert decided["stage"] == IntentLoopStage.PROOF_RECORDED.value
    assert decided["proof"]["governed_success"] is True
