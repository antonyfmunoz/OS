"""P4S-31 — UMH MVP intent→proof operating-loop skeleton tests.

Proves the packet's required behavior and hard constraints:

1. Deterministic parse: same raw text → same IntentSpec shape, no network/LLM.
2. Approval gate HOLDS: a fresh loop is AWAITING_APPROVAL with no proof, and it
   cannot reach PROOF_RECORDED without an explicit governed decision.
3. The approval decision routes through a REGISTERED mutation (regression style
   from #197 — intent_loop_approval_decision is in the real MutationRegistry),
   and its spec is degraded-safe (low-risk, LOCAL_FILE) so the gate stays
   governed even with the daemon down.
4. Governed decision uses governed_mutation (no bypass) — verified at source and
   at runtime (a fake runner captures the exact mutation_name submitted).
5. Proof record shape is stable and its ids come from the real run.
6. No projection-DB import and no provider/adapter import in the intent module.
7. Instance-context clean: no founder/company/product literal in the module.
"""

from __future__ import annotations

import ast
import os
import sys
import tempfile
from pathlib import Path

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _WORKTREE not in sys.path:
    sys.path.insert(0, _WORKTREE)

from substrate.execution.intent.intent_spec import (
    IntentLoopStage,
    IntentSpec,
    IntentKind,
    WorkPacketDraft,
)
from substrate.execution.intent.loop import (
    APPROVAL_MUTATION_NAME,
    IntentLoop,
    IntentLoopStore,
    ProofRecord,
    read_intent_loop_surface,
)
from substrate.organism.mutation_registry import MutationRegistry
from substrate.types import WorkPacketPriority, WorkPacketStatus

_INTENT_DIR = Path(_WORKTREE) / "substrate" / "execution" / "intent"
_SPEC_PATH = _INTENT_DIR / "intent_spec.py"
_LOOP_PATH = _INTENT_DIR / "loop.py"

_BOUNDED_INTENT = "Draft follow-up plan for demo lead pipeline"


def _fresh_loop(tmp_path: str) -> IntentLoop:
    store = IntentLoopStore(store_path=os.path.join(tmp_path, "loops.jsonl"))
    return IntentLoop(store=store)


# ── 1. Deterministic parse ────────────────────────────────────────────────────


def test_intent_spec_parse_is_deterministic():
    """Same input → identical IntentSpec shape (no network, no LLM)."""
    s1 = IntentSpec.from_intent(_BOUNDED_INTENT)
    s2 = IntentSpec.from_intent(_BOUNDED_INTENT)
    assert (s1.raw_text, s1.intent_type, s1.route_type, s1.risk_level) == (
        s2.raw_text,
        s2.intent_type,
        s2.route_type,
        s2.risk_level,
    )
    assert s1.deterministic is True


def test_bounded_directive_is_actionable():
    spec = IntentSpec.from_intent(_BOUNDED_INTENT)
    assert spec.intent_type == IntentKind.DIRECTIVE.value
    draft = spec.to_draft()
    assert isinstance(draft, WorkPacketDraft)
    assert draft.actionable is True
    # Draft reuses the canonical lifecycle vocabulary, not a parallel enum.
    assert draft.status == WorkPacketStatus.PENDING.value
    assert draft.priority in {p.value for p in WorkPacketPriority}


def test_conversation_intent_is_non_actionable():
    """Pure chat must NOT fabricate an actionable work packet."""
    spec = IntentSpec.from_intent("what do you think about our positioning")
    assert spec.intent_type == IntentKind.CONVERSATION.value
    assert spec.to_draft().actionable is False


# ── 2. Approval gate holds ────────────────────────────────────────────────────


def test_submit_holds_at_approval_gate():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        assert rec.stage == IntentLoopStage.AWAITING_APPROVAL.value
        assert rec.proof is None  # no proof before a decision


def test_gate_cannot_reach_proof_without_decision():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        stored = loop._store.get(rec.loop_id)
        assert stored.stage != IntentLoopStage.PROOF_RECORDED.value


def test_invalid_decision_holds_gate():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        out = loop.decide(rec.loop_id, "maybe")
        assert out.stage == IntentLoopStage.AWAITING_APPROVAL.value
        assert out.proof["error"]


def test_second_decision_after_terminal_is_ignored():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        loop.decide(rec.loop_id, "approve")
        again = loop.decide(rec.loop_id, "reject")
        assert again.stage == IntentLoopStage.PROOF_RECORDED.value  # unchanged


# ── 3 & 4. Registered mutation + governed_mutation (no bypass) ────────────────


def test_approval_mutation_is_registered():
    """Regression (#197 style): the approval mutation exists in the real registry."""
    reg = MutationRegistry()
    assert reg.is_registered(APPROVAL_MUTATION_NAME)


def test_approval_spec_is_degraded_safe_and_local():
    reg = MutationRegistry()
    spec = reg.lookup(APPROVAL_MUTATION_NAME)
    assert spec.risk_level == "low"
    assert spec.blast_radius.value in ("local_file", "local_runtime")
    assert spec.degraded_mode_allowed is True


def test_decision_submits_through_governed_runner():
    """The decision must submit exactly the registered mutation name to the
    governed runner — proving no bypass, at runtime."""
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        # Emulate a successful governed execution: run the execute_fn once.
        output, success = kwargs["execute_fn"]()

        class _Resp:
            def __init__(self):
                self.success = success
                self.output = output
                self.envelope_id = "env_test_123"
                self.status = "completed"
                self.degraded = False

        return _Resp()

    with tempfile.TemporaryDirectory() as tmp:
        store = IntentLoopStore(store_path=os.path.join(tmp, "loops.jsonl"))
        loop = IntentLoop(store=store, mutation_runner=fake_runner)
        rec = loop.submit(_BOUNDED_INTENT)
        out = loop.decide(rec.loop_id, "approve")

    assert captured["mutation_name"] == APPROVAL_MUTATION_NAME
    assert callable(captured["execute_fn"])
    assert out.stage == IntentLoopStage.PROOF_RECORDED.value
    assert out.proof["envelope_id"] == "env_test_123"
    assert out.proof["governed_success"] is True


def test_real_governed_mutation_end_to_end():
    """With no injected runner, the loop resolves the REAL governed_mutation and,
    with the daemon down, executes through the substrate fail-closed degraded
    gate — still governed (degraded=True), never ungoverned."""
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)  # no mutation_runner → real governed_mutation
        rec = loop.submit(_BOUNDED_INTENT)
        out = loop.decide(rec.loop_id, "approve")
    assert out.stage == IntentLoopStage.PROOF_RECORDED.value
    assert out.proof["governed_success"] is True
    # Daemon down in the test env → degraded governance path, audited.
    assert out.proof["degraded"] is True
    assert out.proof["governance_status"] == "completed_degraded"


# ── 5. Proof record shape ─────────────────────────────────────────────────────


_PROOF_KEYS = {
    "proof_id",
    "intent_id",
    "draft_id",
    "decision",
    "decided_by",
    "mutation_name",
    "envelope_id",
    "governance_status",
    "governed_success",
    "degraded",
    "resulting_stage",
    "recorded_at",
    "reason",
    "error",
}


def test_proof_record_shape_is_stable():
    with tempfile.TemporaryDirectory() as tmp:
        loop = _fresh_loop(tmp)
        rec = loop.submit(_BOUNDED_INTENT)
        out = loop.decide(rec.loop_id, "approve")
    assert set(out.proof.keys()) == _PROOF_KEYS
    assert out.proof["mutation_name"] == APPROVAL_MUTATION_NAME
    assert isinstance(ProofRecord.from_dict(out.proof), ProofRecord)


def test_read_surface_shape_and_never_raises():
    surface = read_intent_loop_surface()
    for key in (
        "surface",
        "connection_status",
        "total",
        "awaiting_approval",
        "proof_recorded",
        "stage_counts",
        "loops",
        "error",
    ):
        assert key in surface
    assert surface["surface"] == "intent_loop"


# ── 6. No projection-DB / provider imports in the intent module ───────────────


def _module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names.add(a.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_intent_module_has_no_projection_or_provider_imports():
    forbidden_prefixes = (
        "projections.",
        "psycopg2",
        "anthropic",
        "google",
        "adapters.models",
        "openai",
    )
    for path in (_SPEC_PATH, _LOOP_PATH):
        for imp in _module_imports(path):
            assert not imp.startswith(forbidden_prefixes), (
                f"{path.name} imports forbidden module {imp!r} — the intent "
                "skeleton must not touch projection DBs or providers"
            )


def test_loop_governed_path_is_substrate_native_no_transport_import():
    """Governance is obtained by injection OR from the substrate-native canonical
    choke point (route_mutation_degraded). The substrate module must NOT import
    transports/ (dependency-direction law), and must not build a parallel
    mutation runtime."""
    imports = _module_imports(_LOOP_PATH)
    assert not any(i.startswith("transports") for i in imports), (
        "substrate/execution/intent/loop.py must not import transports/"
    )
    src = _LOOP_PATH.read_text(encoding="utf-8")
    # Canonical substrate choke point is the default governed path.
    assert "route_mutation_degraded" in src
    # No parallel mutation runtime construction inside the loop.
    assert "MutationRouter(" not in src
    assert "GovernedExecutionSpine(" not in src


# ── 7. Instance-context clean ─────────────────────────────────────────────────


def test_no_instance_literals_in_intent_module():
    forbidden = (
        "antony",
        "munoz",
        "empyrean",
        "lyfe institute",
        "initiate arena",
        "beast",
        "creatoros",
        "lyfeos",
    )
    for path in (_SPEC_PATH, _LOOP_PATH):
        text = path.read_text(encoding="utf-8").lower()
        for literal in forbidden:
            assert literal not in text, f"{path.name} contains instance literal {literal!r}"
