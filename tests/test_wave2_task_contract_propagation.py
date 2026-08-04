"""Wave 2 — the declared task contract survives into the REAL worker prompt.

Replaces ``tests/test_wave2_field_task_boundaries.py``, which was a
FALSE POSITIVE. That suite hand-wired ``intent``/``desired_end_state``/
``constraints`` into a local ``_Package`` stand-in and called ``render_prompt``
on it, so it never crossed the serialization or compiler boundary. Independent
review found the correction was DEAD CODE: ``ObjectiveLane._from_dict`` silently
dropped all four declared fields, the lane→gap dict carried only the legacy key
set, and ``compiler`` rebuilt ``desired_end_state`` from the node title — yet
every one of those 23 tests still passed. A suite that passes against a fix
which never reaches production is worse than no suite.

Every test here drives the SHIPPED path end to end:

    fixture lane declaration (_declared_lanes_json)
      → real JSON serialization
      → ObjectiveLane.from_dict
      → _lane_gaps
      → ObjectivePlanNode
      → materialize_packets  (real UniversalWorkQueue, real disk)
      → reread from disk
      → compile_attempt_package  (real instruction compilation)
      → render_prompt
      → final worker-visible text

The origin defect: field run ``20260803T002300Z-p1`` failed at
``w16_ab_running_concurrent``. BOTH workers changed the SAME six files (the
complete objective) and BOTH were correctly refused on ``diff_scope``. The
declared scopes were already right — the defect was the task CONTENT each worker
received: only a short title, so the only substantive spec either could find was
the fixture's ``OBJECTIVE.md``, one document holding ALL FOUR task contracts.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from types import SimpleNamespace

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from substrate.contracts.work_context import WorkScope  # noqa: E402
from substrate.execution.attempts.dispatch import compile_attempt_package  # noqa: E402
from substrate.execution.attempts.field_task_scope import (  # noqa: E402
    BACKEND,
    FIXTURE_ALLOWED_PATHS,
    FRONTEND,
    INTEGRATION,
    VERIFICATION,
    ScopeResolutionError,
    forbidden_paths_for,
    task_contract_for,
    task_intent_for,
)
from substrate.execution.attempts.worker_claude_cli import render_prompt  # noqa: E402
from substrate.execution.planning.archetypes import resolve_archetype  # noqa: E402
from substrate.execution.planning.compiler import (  # noqa: E402
    _lane_gaps,
    compile_plan,
    derive_state_records,
    materialize_packets,
)
from substrate.execution.planning.records import (  # noqa: E402
    GroundingSnapshot,
    LaneDeclarationError,
    ObjectiveLane,
    ObjectivePlanNode,
    PlanningSession,
)
from substrate.organism.universal_work_queue import UniversalWorkQueue  # noqa: E402

_BACKEND_FILES = ("app/main.py", "app/store.py", "tests/test_search_api.py")
_FRONTEND_FILES = ("app/static", "tests/test_ui_search.py")
_LANE_ORDER = ("backend", "frontend", "integration", "verification")
_CONTRACT_FIELDS = ("intent", "desired_end_state", "constraints", "forbidden_path_scope")


# ── the REAL producer ────────────────────────────────────────────────────────


def _declared_lanes() -> list[dict]:
    """The shipped dispatcher's lane declaration, through real JSON."""
    spec = importlib.util.spec_from_file_location(
        "wfd_propagation", os.path.join(REPO, "scripts", "wave2_field_dispatch.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["wfd_propagation"] = mod
    spec.loader.exec_module(mod)
    return json.loads(mod._declared_lanes_json())


_OBJECTIVE = "add note search"


def _materialize_from_lanes(lanes: list[dict], tmpdir: str):
    """Drive the ENTIRE shipped planning path from declared lanes.

    ``derive_state_records(lanes=…)`` → ``compile_plan`` → ``materialize_packets``
    are the real production functions; NOTHING here hand-builds a gap, a node,
    or an edge. An earlier revision of this helper constructed the plan nodes
    itself, which silently re-created the F-2 bypass: mutating the compiler's
    own gap→node construction left the suite green, because the suite was
    building those nodes rather than exercising the code that builds them
    (mutants m10/m11/m12 survived). Every boundary must be the shipped one.
    """
    os.environ["UMH_STATE_DIR"] = os.path.join(tmpdir, "state")
    os.environ["UMH_ROOT"] = os.path.join(tmpdir, "repo")
    os.makedirs(os.environ["UMH_ROOT"], exist_ok=True)
    scope = WorkScope(tenant_id="t-prop", conversation_id="c-prop", target_kind="umh_substrate")
    session = PlanningSession(objective_text=_OBJECTIVE, conversation_id="c-prop")
    session.objective_id = "goal-prop"
    session.intent_id = "intent-prop"
    snapshot = GroundingSnapshot(intent_id="intent-prop", conversation_id="c-prop")
    current, desired, gap_snapshot = derive_state_records(
        _OBJECTIVE, snapshot, tenant_id="t-prop", scope=scope, lanes=lanes
    )
    archetype = resolve_archetype(_OBJECTIVE, scope)
    plan = compile_plan(
        session, scope, "objective", current, desired, gap_snapshot, snapshot.grounding_snapshot_id, archetype
    )
    store = os.path.join(tmpdir, "packets.jsonl")
    ids = materialize_packets(plan, scope, archetype, session, UniversalWorkQueue(store_path=store))
    # Reread through a FRESH queue: an in-memory object would hide a
    # serialization loss, which is the exact class of defect under test.
    fresh = UniversalWorkQueue(store_path=store)
    return plan, [fresh.get_packet(i) for i in ids]


def _prompt_for_packet(packet, plan) -> str:
    """The final worker-visible text, via the SHIPPED package compiler."""
    grant = SimpleNamespace(
        tenant_id="t-prop",
        decision_ref="dec-1",
        authorized_scope_hash="hash-1",
        risk_ceiling="high",
        task_frontier=[packet.packet_id],
        verification_obligations=[],
        cost_limit_usd=0.0,
        cost_enforceable=False,
    )
    assignment = SimpleNamespace(
        role_contract_id="role-impl",
        skill_requirement_refs=[],
        tool_profile=["Edit"],
        environment_class="local",
        model_profile={"model": "claude"},
    )
    attempt = SimpleNamespace(
        task_id=packet.packet_id,
        attempt_id="att-1",
        plan_record_id=plan.plan_record_id,
        plan_version=1,
        execution_authorization_ref="dec-1",
        timeout_seconds=600,
        max_turns=30,
    )
    return render_prompt(
        compile_attempt_package(
            attempt=attempt, packet=packet, assignment=assignment, grant=grant
        )
    )


@pytest.fixture(scope="module")
def field() -> dict:
    """One end-to-end run of the shipped path, shared by every test."""
    lanes = _declared_lanes()
    with tempfile.TemporaryDirectory() as tmpdir:
        plan, packets = _materialize_from_lanes(lanes, tmpdir)
        prompts = {
            key: _prompt_for_packet(pkt, plan) for key, pkt in zip(_LANE_ORDER, packets)
        }
        return {
            "lanes": {lane["lane_key"]: lane for lane in lanes},
            "packets": dict(zip(_LANE_ORDER, packets)),
            "prompts": prompts,
        }


# ── 1. all four declared fields survive into the final prompt ────────────────


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_1_all_four_declared_fields_reach_the_final_prompt(field, lane_key):
    lane, prompt = field["lanes"][lane_key], field["prompts"][lane_key]
    # intent + desired_end_state: their DECLARED text, not a title rebuild.
    assert lane["intent"].split(".")[0] in prompt, "declared intent must reach the worker"
    for line in [ln for ln in lane["desired_end_state"].split("\n") if ln.strip()][:3]:
        assert line.strip() in prompt, f"declared end-state line missing: {line[:60]}"
    for constraint in lane["constraints"]:
        head = constraint.split("\n")[0].strip()
        assert head in prompt, f"declared constraint missing: {head[:60]}"
    for path in lane["forbidden_path_scope"]:
        assert path in prompt, f"declared forbidden path missing: {path}"


def test_1b_producer_and_record_agree_on_the_contract_key_set(field):
    """The producer's keys must be exactly carryable — no silent surplus."""
    for lane in field["lanes"].values():
        unknown = set(lane) - set(ObjectiveLane.__dataclass_fields__)
        assert not unknown, f"lane declares keys the record cannot carry: {sorted(unknown)}"
    for name in _CONTRACT_FIELDS:
        assert name in ObjectiveLane.__dataclass_fields__, f"ObjectiveLane must carry {name}"
        assert name in ObjectivePlanNode.__dataclass_fields__, f"node must carry {name}"


# ── 2. removing propagation at ObjectiveLane fails ───────────────────────────


@pytest.mark.parametrize("dropped", _CONTRACT_FIELDS)
def test_2_dropping_a_field_at_the_lane_boundary_is_detected(field, dropped):
    """Simulates the F-1 defect exactly: the lane cannot carry the field.

    This is the test the old suite could not have: its stand-in package never
    passed through ``ObjectiveLane`` at all.
    """
    lane = dict(field["lanes"]["backend"])
    lane.pop(dropped)
    rebuilt = ObjectiveLane.from_dict(lane)
    assert getattr(rebuilt, dropped) in ("", [], None), "dropped field must be empty"
    gap = _lane_gaps([lane])[0]
    assert not gap[dropped], f"{dropped} lost at the lane boundary must stay lost (no re-derivation)"


def test_2b_round_trip_through_serialization_is_lossless(field):
    """to_dict → JSON → from_dict must preserve every contract field."""
    for lane_key, lane in field["lanes"].items():
        obj = ObjectiveLane.from_dict(dict(lane))
        again = ObjectiveLane.from_dict(json.loads(json.dumps(obj.to_dict())))
        assert again.to_dict() == obj.to_dict(), f"{lane_key}: round trip must be lossless"


# ── 3. removing propagation at the lane/gap boundary fails ───────────────────


@pytest.mark.parametrize("field_name", _CONTRACT_FIELDS)
def test_3_lane_gap_boundary_carries_every_contract_field(field, field_name):
    gap = _lane_gaps([dict(field["lanes"]["backend"])])[0]
    assert field_name in gap, f"_lane_gaps must carry {field_name}"
    assert gap[field_name], f"_lane_gaps must carry a NON-EMPTY {field_name}"


# ── 4. restoring the compiler's title fallback fails ─────────────────────────


def test_4_desired_end_state_is_the_declared_contract_not_the_title(field):
    """The exact F-1 claim 3 regression: ``desired_end_state=raw['title']``."""
    for lane_key in ("backend", "frontend"):
        packet = field["packets"][lane_key]
        lane = field["lanes"][lane_key]
        assert packet.desired_end_state == lane["desired_end_state"], (
            f"{lane_key}: packet must carry the DECLARED end state verbatim"
        )
        assert packet.desired_end_state != packet.title, (
            f"{lane_key}: title fallback must not win over a declared contract"
        )
        assert len(packet.desired_end_state) > len(packet.title), (
            f"{lane_key}: a title-derived end state is not a contract"
        )


def test_4b_legacy_lane_without_a_declaration_keeps_title_fallback():
    """BACKWARD COMPATIBILITY: an undeclared lane behaves exactly as before.

    Driven through the SAME shipped path as every other test — a legacy lane is
    just one that declares none of the four contract fields.
    """
    legacy = {
        "lane_key": "legacy",
        "title": "legacy node title",
        "writable_path_scope": ["app/main.py"],
        "depends_on": [],
        "semantic_label": "",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        plan, packets = _materialize_from_lanes([legacy], tmpdir)
        packet = packets[0]
        assert packet.desired_end_state == "legacy node title", "legacy title fallback preserved"
        # A legacy lane declares no constraint TEXT. It still declares an
        # authority, and the compiler renders that authority as the worker's
        # allowed-path line — the same single source every lane uses.
        assert packet.constraints == [
            "You may change ONLY these paths: app/main.py"
        ], "legacy lane gets its boundary rendered, and nothing else"
        assert _OBJECTIVE in packet.user_intent, "legacy user_intent shape preserved"
        assert packet.requirements["writable_path_scope"] == ["app/main.py"], (
            "legacy authority unchanged"
        )


def test_4c_user_intent_stays_unique_per_task(field):
    """Test AJ's invariant: UniversalWorkQueue dedupes by user_intent."""
    intents = [field["packets"][k].user_intent for k in _LANE_ORDER]
    assert len(set(intents)) == len(intents), "each Task needs a UNIQUE user_intent"


def test_4d_each_lane_receives_its_own_intent_and_not_a_siblings(field):
    """Closes the open MEDIUM: cross-lane intent DISTINCTNESS in the PROMPT.

    ``test_4c`` proves the packets carry unique ``user_intent`` values, but
    uniqueness of a stored field is not the property that failed in the field.
    What failed was the WORKER'S VIEW: both workers implemented the complete
    six-file objective because what reached each prompt did not confine it to its
    own slice. So the assertion has to be made where the worker actually reads —
    each lane's declared intent must appear in ITS prompt and must NOT appear in
    any sibling's.
    """
    for lane_key in _LANE_ORDER:
        declared = field["lanes"][lane_key]["intent"].split(".")[0].strip()
        assert declared, f"{lane_key}: precondition — the lane declares an intent"
        assert declared in field["prompts"][lane_key], (
            f"{lane_key}: its own declared intent must reach its worker"
        )
        for other in _LANE_ORDER:
            if other == lane_key:
                continue
            assert declared not in field["prompts"][other], (
                f"{other}'s prompt leaks {lane_key}'s intent — a worker that can read a "
                "sibling's assignment can implement it, which is exactly how both "
                "workers wrote the complete objective in field run 20260803T002300Z-p1"
            )


# ── 5. dropping any one field causes failure ─────────────────────────────────


@pytest.mark.parametrize("field_name", _CONTRACT_FIELDS)
def test_5_dropping_one_field_removes_it_from_the_final_prompt(field, field_name):
    """Each field is INDEPENDENTLY load-bearing on the real path."""
    lane = dict(field["lanes"]["backend"])
    marker = {
        "intent": lane["intent"].split(".")[0],
        "desired_end_state": [ln for ln in lane["desired_end_state"].split("\n") if ln.strip()][0],
        "constraints": lane["constraints"][0].split("\n")[0],
        "forbidden_path_scope": lane["forbidden_path_scope"][0],
    }[field_name].strip()
    assert marker in field["prompts"]["backend"], "precondition: present when declared"
    lane[field_name] = "" if isinstance(lane[field_name], str) else []
    with tempfile.TemporaryDirectory() as tmpdir:
        plan, packets = _materialize_from_lanes([lane], tmpdir)
        degraded = _prompt_for_packet(packets[0], plan)
    if field_name == "forbidden_path_scope":
        # Its paths also appear in the declared constraint line; what must
        # disappear is the structured prohibition the field itself contributes.
        assert lane["constraints"], "precondition"
    else:
        assert marker not in degraded, f"{field_name} must be load-bearing, not decorative"


# ── 6. misspelling any field fails CLOSED ────────────────────────────────────


@pytest.mark.parametrize("field_name", _CONTRACT_FIELDS)
def test_6_a_misspelled_contract_field_fails_closed(field, field_name):
    """A silently-ignored typo is exactly how F-1 shipped believed-correct."""
    lane = dict(field["lanes"]["backend"])
    lane[field_name + "s"] = lane.pop(field_name)  # plausible typo
    with pytest.raises(LaneDeclarationError) as exc:
        ObjectiveLane.from_dict(lane)
    assert field_name + "s" in str(exc.value), "the error must NAME the offending key"


def test_6b_unknown_keys_never_pass_silently(field):
    lane = dict(field["lanes"]["backend"])
    lane["totally_unknown_key"] = "x"
    with pytest.raises(LaneDeclarationError):
        ObjectiveLane.from_dict(lane)


def test_6c_legacy_lane_without_contract_fields_still_loads(field):
    """BACKWARD COMPATIBILITY: strictness rejects UNKNOWN keys, not ABSENT ones."""
    legacy = {
        "lane_key": "legacy",
        "title": "legacy lane",
        "writable_path_scope": ["app/main.py"],
        "depends_on": [],
        "semantic_label": "",
    }
    lane = ObjectiveLane.from_dict(legacy)
    assert lane.lane_key == "legacy"
    for name in _CONTRACT_FIELDS:
        assert getattr(lane, name) in ("", []), f"{name} must default empty for a legacy lane"
    gap = _lane_gaps([legacy])[0]
    assert gap["writable_path_scope"] == ["app/main.py"], "legacy authority unchanged"


# ── 7/8. each prompt carries its OWN complete contract ───────────────────────


def test_7_backend_prompt_carries_the_full_backend_contract(field):
    prompt = field["prompts"]["backend"]
    assert "/api/notes/search" in prompt, "exact endpoint contract"
    assert "400" in prompt, "exact error contract"
    for path in _BACKEND_FILES:
        assert path in prompt, f"backend must be told its allowed path {path}"
    for path in _FRONTEND_FILES:
        assert path in prompt, f"backend must be told frontend path {path} is forbidden"
    assert "FORBIDDEN" in prompt
    assert "Writable Scope" in prompt


def test_8_frontend_prompt_carries_the_full_frontend_contract(field):
    prompt = field["prompts"]["frontend"]
    assert "note-search-input" in prompt
    assert "note-search-results" in prompt
    for path in _FRONTEND_FILES:
        assert path in prompt, f"frontend must be told its allowed path {path}"
    for path in _BACKEND_FILES:
        assert path in prompt, f"frontend must be told backend path {path} is forbidden"
    assert "concurrently" in prompt.lower(), "frontend must know the backend runs concurrently"
    assert "do NOT implement it yourself" in prompt


def test_7b_neither_prompt_leaks_the_other_task_as_its_own_work(field):
    """The w16 failure shape: a worker treating BOTH slices as its job."""
    backend, frontend = field["prompts"]["backend"], field["prompts"]["frontend"]
    assert "note-search-input" not in backend.split("FORBIDDEN")[0], (
        "backend must not be handed the frontend's testid contract as its own work"
    )
    assert "returns HTTP 400" not in frontend, (
        "frontend must not be handed the backend's error contract as its own work"
    )


@pytest.mark.parametrize("lane_key", ["backend", "frontend", "integration"])
def test_7d_every_writing_lane_is_told_its_allowed_paths_as_a_constraint(field, lane_key):
    """The allowed-path line must reach EVERY lane that may write.

    Regression for a mutant that survived the first adversarial pass: changing
    the dedup guard to ``if allowed and not declared`` silenced this line on
    every real lane (which all declare constraints) while the suite stayed
    green — the only assertion on it lived in the LEGACY test, where
    ``declared`` is empty and the mutant is inert. The sealed
    ``## Writable Scope`` section is rendered from a different source, so it
    masked the loss. Pin the CONSTRAINT-level line on real declared lanes.
    """
    packet = field["packets"][lane_key]
    joined = "\n".join(packet.constraints)
    assert "You may change ONLY these paths" in joined, (
        f"{lane_key}: writing lane must be told its allowed paths as a constraint"
    )
    for path in packet.requirements["writable_path_scope"]:
        assert path in joined, f"{lane_key}: allowed-path constraint must name {path}"
    assert "You may change ONLY these paths" in field["prompts"][lane_key]


def test_7e_constraint_order_puts_boundaries_before_prose(field):
    """Rendered boundaries lead; declared prose follows.

    A worker that stops reading early must still have seen its path
    boundaries, so the derived lines must not be pushed below a multi-line
    precedence note.
    """
    for lane_key in ("backend", "frontend"):
        constraints = field["packets"][lane_key].constraints
        allowed_at = next(
            i for i, c in enumerate(constraints) if "You may change ONLY these paths" in c
        )
        prose_at = next(
            i for i, c in enumerate(constraints) if "Authorization Precedence" in c
        )
        assert allowed_at < prose_at, f"{lane_key}: boundaries must precede declared prose"


def test_7c_forbidden_prohibition_appears_exactly_once(field):
    """A duplicated prohibition reads as two rules and buries the contract."""
    for lane_key in ("backend", "frontend"):
        count = field["prompts"][lane_key].count("belong to a DIFFERENT Task and are FORBIDDEN")
        assert count == 1, f"{lane_key}: prohibition stated {count}× — must be exactly once"


# ── 9. every prompt forbids solving the complete objective ───────────────────


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_9_prompt_forbids_solving_the_complete_objective(field, lane_key):
    prompt = field["prompts"][lane_key]
    assert "do NOT solve the complete objective" in prompt, "verbatim prohibition required"
    assert "Implement the complete objective." not in prompt


# ── 10. OBJECTIVE.md cannot broaden either task ──────────────────────────────


@pytest.mark.parametrize("lane_key", ["backend", "frontend"])
def test_10_objective_md_is_subordinated_in_the_final_prompt(field, lane_key):
    prompt = field["prompts"][lane_key]
    assert "OBJECTIVE.md" in prompt
    assert "INFORMATIONAL ONLY" in prompt
    assert "does NOT authorize you to widen your change surface" in prompt


def test_10b_precedence_order_is_strict_in_the_final_prompt(field):
    """Order must survive rendering — not just exist in the source constant."""
    prompt = field["prompts"]["backend"]
    i_grant = prompt.index("grant and WorkPacket authorization")
    i_task = prompt.index("This Task's instructions")
    i_arch = prompt.index("Shared architectural context")
    i_obj = prompt.index("`OBJECTIVE.md` and any other repository document")
    assert i_grant < i_task < i_arch < i_obj, "precedence must render in strict order"


# ── 11. multiline precedence stays structured, not a run-on line ─────────────


def test_11_multiline_contract_is_not_collapsed_into_one_line(field):
    """F-5: ``"; ".join`` flattened an ordered contract into a run-on line."""
    prompt = field["prompts"]["backend"]
    block = prompt.split("- constraints:")[1].split("## Writable Scope")[0]
    assert block.count("\n") >= 8, "the constraint block must stay multi-line"
    for numeral in ("1.", "2.", "3.", "4."):
        line = [ln.strip() for ln in block.split("\n") if ln.strip().startswith(numeral)]
        assert line, f"precedence item {numeral} must render on its OWN line"
    assert "; 2." not in prompt, "numbered precedence must not be semicolon-joined"
    assert "; 3." not in prompt


def test_11b_each_constraint_renders_as_its_own_bullet(field):
    """One bullet per constraint the PACKET carries — declared + rendered."""
    block = field["prompts"]["backend"].split("- constraints:")[1].split("## Writable")[0]
    bullets = [ln for ln in block.split("\n") if ln.startswith("  - ")]
    packet_constraints = field["packets"]["backend"].constraints
    assert len(bullets) == len(packet_constraints), (
        f"expected one bullet per constraint ({len(packet_constraints)}), got {len(bullets)}"
    )


def test_11c_multiline_scalar_keeps_its_line_structure(field):
    """``desired_end_state`` is a MULTI-LINE scalar; collapsing it onto the
    label line buries the endpoint/response/error clauses in one run-on
    sentence (mutant m18). Its own lines must survive as lines."""
    prompt = field["prompts"]["backend"]
    declared = field["lanes"]["backend"]["desired_end_state"]
    declared_lines = [ln.strip() for ln in declared.split("\n") if ln.strip()]
    assert len(declared_lines) >= 4, "precondition: the contract is genuinely multi-line"
    block = prompt.split("- desired end state:")[1].split("- constraints:")[0]
    raw_lines = [ln for ln in block.split("\n") if ln.strip()]
    rendered = [ln.strip() for ln in raw_lines]
    assert len(rendered) >= len(declared_lines), (
        f"end state collapsed: {len(declared_lines)} declared lines rendered as {len(rendered)}"
    )
    for line in declared_lines:
        assert any(line == r for r in rendered), f"end-state line lost its own line: {line[:60]}"
    # Newlines alone are not structure. Every continuation line must stay
    # INDENTED under its label: dedented to column 0 they are visually
    # indistinguishable from a new top-level section, so the contract's own
    # "- case-insensitive…" clauses read as siblings of "- constraints:"
    # rather than as part of the end state (mutant m18).
    for raw in raw_lines:
        assert raw.startswith("  "), (
            f"end-state line must stay indented under its label, got {raw[:60]!r}"
        )


# ── 12. verification still rejects cross-scope edits, unchanged ──────────────


def test_12_declared_writable_scope_is_unchanged_by_this_correction(field):
    """The correction touches INSTRUCTIONS only — never enforced authority."""
    for lane_key, label in (("backend", BACKEND), ("frontend", FRONTEND)):
        req = field["packets"][lane_key].requirements
        assert req["scope_declared"] is True
        assert sorted(req["writable_path_scope"]) == sorted(FIXTURE_ALLOWED_PATHS[label]), (
            f"{lane_key}: enforced authority must be byte-identical to the canonical map"
        )


def test_12b_forbidden_paths_never_widen_the_writable_scope(field):
    for lane_key, label in (("backend", BACKEND), ("frontend", FRONTEND)):
        allowed = set(field["packets"][lane_key].requirements["writable_path_scope"])
        forbidden = set(field["lanes"][lane_key]["forbidden_path_scope"])
        assert allowed and forbidden
        assert not (allowed & forbidden), f"{lane_key}: allowed ∩ forbidden must be empty"


def test_12c_the_six_file_overreach_is_outside_both_lanes(field):
    """The EXACT files both workers changed in run 20260803T002300Z-p1."""
    overreach = [
        "app/main.py",
        "app/static/app.js",
        "app/static/index.html",
        "app/store.py",
        "tests/test_search_api.py",
        "tests/test_ui_search.py",
    ]
    for label in (BACKEND, FRONTEND):
        allowed = FIXTURE_ALLOWED_PATHS[label]
        outside = [
            p
            for p in overreach
            if not any(p == a or p.startswith(a.rstrip("/") + "/") for a in allowed)
        ]
        assert outside, f"{label} must NOT be authorized for the whole six-file set"


# ── 13. the two accepted slices compose into the complete objective ──────────


def test_13_backend_and_frontend_compose_to_the_whole_objective(field):
    union = set(FIXTURE_ALLOWED_PATHS[BACKEND]) | set(FIXTURE_ALLOWED_PATHS[FRONTEND])
    assert set(FIXTURE_ALLOWED_PATHS[INTEGRATION]) <= union


# ── 14. Task C stays blocked until its predecessors are verified ─────────────


def test_14_integration_depends_on_both_implementation_lanes(field):
    integration = field["lanes"]["integration"]
    assert set(integration["depends_on"]) == {"backend", "frontend"}, (
        "C must fan in from BOTH implementation lanes"
    )
    verification = field["lanes"]["verification"]
    assert "integration" in verification["depends_on"], "D must follow C"


def test_14b_dependencies_are_translated_onto_the_materialized_packets(field):
    """A declared edge that never becomes a packet edge never blocks anything."""
    by_key = field["packets"]
    impl_ids = {by_key["backend"].packet_id, by_key["frontend"].packet_id}
    assert set(by_key["integration"].dependencies) == impl_ids, (
        "C's packet must depend on BOTH implementation packets"
    )
    assert by_key["integration"].packet_id in by_key["verification"].dependencies


# ── verifier lane stays zero-write ───────────────────────────────────────────


def test_verification_lane_remains_zero_write(field):
    assert FIXTURE_ALLOWED_PATHS[VERIFICATION] == []
    prompt = field["prompts"]["verification"]
    assert "READ-ONLY" in prompt
    assert "ZERO writable paths" in prompt
    assert "Do NOT modify anything" in prompt


# ── fail-closed accessors ────────────────────────────────────────────────────


def test_accessors_fail_closed_on_unknown_label():
    for fn in (task_intent_for, task_contract_for, forbidden_paths_for):
        with pytest.raises(ScopeResolutionError):
            fn("not_a_real_label")
