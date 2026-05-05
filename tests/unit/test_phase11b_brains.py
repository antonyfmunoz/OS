"""
Tests for Phase 11B — Substrate-Expression Protocol v1.

Verifies:
  - BrainProfile creation, validation, serialization
  - ExpressionState mutations, clamping, correction application
  - ExpressionState inheritance
  - BrainRegistry CRUD, children, create_child
  - resolve_with_inheritance merges correctly
  - ensure_default_brains idempotency
  - BrainSignal append-only store, filtering, targeting
  - Boundary checks: no execution imports in brain modules
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
import re
import os

from umh.brains.profile import (
    AuthorityLevel,
    BrainProfile,
    ExpressionState,
    _clamp,
)
from umh.brains.registry import (
    apply_correction,
    children,
    clear,
    create_child,
    ensure_default_brains,
    get,
    get_expression,
    list_all,
    list_brains,
    register,
    resolve_with_inheritance,
    update_expression,
    BrainRegistry,
    get_brain_registry,
)
from umh.brains.signals import (
    BrainSignal,
    clear as clear_signals,
    emit_signal,
    get_signal,
    list_all_signals,
    list_signals,
    list_signals_for_target,
    signal_count,
)


# ─── BrainProfile ──────────────────────────────────────────────────


def test_profile_creation():
    p = BrainProfile(brain_id="test", name="Test")
    assert p.brain_id == "test"
    assert p.name == "Test"
    assert p.brain_type == "system"
    assert p.authority == AuthorityLevel.ADVISE
    assert p.created_at != ""
    assert p.updated_at == p.created_at
    print("  PASS: profile_creation")


def test_profile_validation():
    try:
        BrainProfile(brain_id="", name="X")
        assert False, "Should have raised"
    except ValueError:
        pass

    try:
        BrainProfile(brain_id="x", name="")
        assert False, "Should have raised"
    except ValueError:
        pass
    print("  PASS: profile_validation")


def test_profile_frozen():
    p = BrainProfile(brain_id="test", name="Test")
    try:
        p.name = "Other"
        assert False, "Should have raised"
    except AttributeError:
        pass
    print("  PASS: profile_frozen")


def test_profile_serialization():
    p = BrainProfile(
        brain_id="ser",
        name="Serialization",
        brain_type="agent",
        authority=AuthorityLevel.EXECUTE,
        active_primitives=("action", "change"),
        amplified_concepts=frozenset({"build"}),
        silenced_concepts=frozenset({"email"}),
        preferred_patterns=("builder",),
        retrieval_weights={"memory": 1.5},
        tool_permissions=("shell",),
        metadata={"key": "val"},
    )
    d = p.to_dict()
    assert d["brain_id"] == "ser"
    assert d["authority"] == "execute"
    assert "action" in d["active_primitives"]
    assert "build" in d["amplified_concepts"]
    assert d["retrieval_weights"]["memory"] == 1.5

    serialized = json.dumps(d)
    assert '"brain_id"' in serialized

    p2 = BrainProfile.from_dict(d)
    assert p2.brain_id == p.brain_id
    assert p2.authority == AuthorityLevel.EXECUTE
    assert p2.amplified_concepts == frozenset({"build"})
    print("  PASS: profile_serialization")


# ─── ExpressionState ───────────────────────────────────────────────


def test_expression_amplify():
    s = ExpressionState(brain_id="test")
    s.amplify("revenue", 0.8)
    assert s.amplified_concepts["revenue"] == 0.8
    assert "revenue" not in s.silenced_concepts
    assert s.checkpoint_version == 1
    print("  PASS: expression_amplify")


def test_expression_silence():
    s = ExpressionState(brain_id="test")
    s.amplify("x", 0.5)
    s.silence("x", 0.9)
    assert "x" not in s.amplified_concepts
    assert s.silenced_concepts["x"] == 0.9
    assert s.checkpoint_version == 2
    print("  PASS: expression_silence")


def test_expression_prefer_pattern():
    s = ExpressionState(brain_id="test")
    s.prefer_pattern("builder", 0.7)
    assert s.preferred_patterns["builder"] == 0.7
    assert s.checkpoint_version == 1
    print("  PASS: expression_prefer_pattern")


def test_expression_clamping():
    assert _clamp(-0.5) == 0.0
    assert _clamp(1.5) == 1.0
    assert _clamp(0.5) == 0.5

    s = ExpressionState(brain_id="test")
    s.amplify("x", 5.0)
    assert s.amplified_concepts["x"] == 1.0

    s.silence("y", -1.0)
    assert s.silenced_concepts["y"] == 0.0
    print("  PASS: expression_clamping")


def test_expression_apply_correction():
    s = ExpressionState(brain_id="test")
    s.apply_correction(
        {
            "type": "amplify",
            "value": {"strategy": 0.8, "revenue": 0.6},
            "reason": "test",
        }
    )
    assert s.amplified_concepts["strategy"] == 0.8
    assert s.amplified_concepts["revenue"] == 0.6
    assert len(s.learned_corrections) == 1
    assert s.learned_corrections[0]["type"] == "amplify"

    s.apply_correction(
        {
            "type": "silence",
            "value": {"deploy": 0.9},
        }
    )
    assert s.silenced_concepts["deploy"] == 0.9
    assert len(s.learned_corrections) == 2

    s.apply_correction(
        {
            "type": "prefer_pattern",
            "value": {"builder": 0.7},
        }
    )
    assert s.preferred_patterns["builder"] == 0.7
    assert len(s.learned_corrections) == 3
    print("  PASS: expression_apply_correction")


def test_expression_correction_adds_timestamp():
    s = ExpressionState(brain_id="test")
    correction = {"type": "amplify", "value": {"x": 0.5}}
    s.apply_correction(correction)
    assert "timestamp" in s.learned_corrections[0]
    print("  PASS: expression_correction_adds_timestamp")


def test_expression_inherit():
    parent = ExpressionState(brain_id="parent")
    parent.amplify("strategy", 0.8)
    parent.silence("deploy", 0.9)
    parent.prefer_pattern("ceo", 0.7)
    parent.concept_weights["x"] = 0.5
    parent.suppressed_intents.add("monitoring")
    parent.pattern_bias["builder"] = 1.5

    child = ExpressionState.inherit(parent, "child")
    assert child.brain_id == "child"
    assert child.inherited_from == "parent"
    assert child.amplified_concepts["strategy"] == 0.8
    assert child.silenced_concepts["deploy"] == 0.9
    assert child.preferred_patterns["ceo"] == 0.7
    assert child.concept_weights["x"] == 0.5
    assert "monitoring" in child.suppressed_intents
    assert child.pattern_bias["builder"] == 1.5
    assert child.checkpoint_version == 0
    assert child.learned_corrections == []
    print("  PASS: expression_inherit")


def test_expression_serialization():
    s = ExpressionState(brain_id="test")
    s.amplify("x", 0.5)
    s.silence("y", 0.3)
    s.suppressed_intents.add("monitoring")

    d = s.to_dict()
    assert d["brain_id"] == "test"
    assert d["amplified_concepts"]["x"] == 0.5
    assert "monitoring" in d["suppressed_intents"]

    s2 = ExpressionState.from_dict(d)
    assert s2.brain_id == "test"
    assert s2.amplified_concepts["x"] == 0.5
    assert "monitoring" in s2.suppressed_intents
    print("  PASS: expression_serialization")


# ─── Registry ──────────────────────────────────────────────────────


def test_registry_crud():
    clear()
    p = BrainProfile(brain_id="r1", name="R1", brain_type="agent")
    register(p)

    assert get("r1") is not None
    assert get("r1").name == "R1"
    assert get("nonexistent") is None
    assert "r1" in list_brains()
    assert len(list_all()) == 1
    print("  PASS: registry_crud")


def test_registry_auto_expression_state():
    clear()
    p = BrainProfile(brain_id="r2", name="R2")
    register(p)

    state = get_expression("r2")
    assert state is not None
    assert state.brain_id == "r2"
    print("  PASS: registry_auto_expression_state")


def test_registry_explicit_expression_state():
    clear()
    p = BrainProfile(brain_id="r3", name="R3")
    s = ExpressionState(brain_id="r3")
    s.amplify("test_concept", 0.9)
    register(p, s)

    state = get_expression("r3")
    assert state is not None
    assert state.amplified_concepts["test_concept"] == 0.9
    print("  PASS: registry_explicit_expression_state")


def test_registry_update_expression():
    clear()
    p = BrainProfile(brain_id="r4", name="R4")
    register(p)

    s = ExpressionState(brain_id="r4")
    s.amplify("x", 0.5)
    update_expression("r4", s)

    state = get_expression("r4")
    assert state.amplified_concepts["x"] == 0.5
    print("  PASS: registry_update_expression")


def test_registry_apply_correction():
    clear()
    p = BrainProfile(brain_id="r5", name="R5")
    register(p)

    ok = apply_correction("r5", {"type": "amplify", "value": {"x": 0.7}})
    assert ok

    state = get_expression("r5")
    assert state.amplified_concepts["x"] == 0.7

    not_ok = apply_correction("nonexistent", {"type": "amplify", "value": {"x": 0.7}})
    assert not not_ok
    print("  PASS: registry_apply_correction")


def test_registry_children():
    clear()
    parent = BrainProfile(brain_id="parent", name="Parent")
    child1 = BrainProfile(brain_id="child1", name="Child 1", parent_brain_id="parent")
    child2 = BrainProfile(brain_id="child2", name="Child 2", parent_brain_id="parent")
    orphan = BrainProfile(brain_id="orphan", name="Orphan")
    register(parent)
    register(child1)
    register(child2)
    register(orphan)

    kids = children("parent")
    assert len(kids) == 2
    kid_ids = {k.brain_id for k in kids}
    assert "child1" in kid_ids
    assert "child2" in kid_ids
    assert "orphan" not in kid_ids
    print("  PASS: registry_children")


def test_registry_create_child():
    clear()
    parent = BrainProfile(
        brain_id="parent",
        name="Parent",
        authority=AuthorityLevel.ADMIN,
        active_primitives=("state", "goal"),
        amplified_concepts=frozenset({"strategy"}),
        retrieval_weights={"memory": 1.5},
    )
    register(parent)

    state = get_expression("parent")
    state.amplify("revenue", 0.8)
    update_expression("parent", state)

    child = create_child("parent", "Project Alpha", brain_type="project")
    assert child is not None
    assert child.brain_id == "parent.project_alpha"
    assert child.parent_brain_id == "parent"
    assert child.authority == AuthorityLevel.ADMIN
    assert "state" in child.active_primitives
    assert "goal" in child.active_primitives
    assert "strategy" in child.amplified_concepts

    child_expr = get_expression(child.brain_id)
    assert child_expr is not None
    assert child_expr.inherited_from == "parent"
    assert child_expr.amplified_concepts["revenue"] == 0.8

    none_result = create_child("nonexistent", "Fail")
    assert none_result is None
    print("  PASS: registry_create_child")


def test_registry_create_child_with_overrides():
    clear()
    parent = BrainProfile(brain_id="p", name="P", authority=AuthorityLevel.ADMIN)
    register(parent)

    child = create_child(
        "p",
        "Override",
        overrides={
            "brain_id": "custom_id",
            "authority": "execute",
            "scope": {"project": "alpha"},
        },
    )
    assert child is not None
    assert child.brain_id == "custom_id"
    assert child.authority == AuthorityLevel.EXECUTE
    assert child.scope["project"] == "alpha"
    print("  PASS: registry_create_child_with_overrides")


def test_resolve_with_inheritance():
    clear()
    parent = BrainProfile(
        brain_id="parent",
        name="Parent",
        authority=AuthorityLevel.ADMIN,
        active_primitives=("state", "goal"),
        amplified_concepts=frozenset({"strategy", "revenue"}),
        silenced_concepts=frozenset({"deploy"}),
        preferred_patterns=("ceo",),
        retrieval_weights={"memory": 1.5, "events": 0.5},
        scope={"level": "org"},
    )
    child = BrainProfile(
        brain_id="child",
        name="Child",
        authority=AuthorityLevel.EXECUTE,
        active_primitives=("action", "change"),
        amplified_concepts=frozenset({"build", "code"}),
        silenced_concepts=frozenset({"email"}),
        preferred_patterns=("builder",),
        retrieval_weights={"memory": 2.0},
        parent_brain_id="parent",
        scope={"project": "alpha"},
    )
    register(parent)
    register(child)

    resolved = resolve_with_inheritance("child")
    assert resolved is not None

    assert resolved.brain_id == "child"
    assert resolved.authority == AuthorityLevel.EXECUTE

    assert "strategy" in resolved.amplified_concepts
    assert "revenue" in resolved.amplified_concepts
    assert "build" in resolved.amplified_concepts
    assert "code" in resolved.amplified_concepts

    assert "deploy" in resolved.silenced_concepts
    assert "email" in resolved.silenced_concepts

    assert "state" in resolved.active_primitives
    assert "goal" in resolved.active_primitives
    assert "action" in resolved.active_primitives
    assert "change" in resolved.active_primitives

    assert resolved.retrieval_weights["memory"] == 2.0
    assert resolved.retrieval_weights["events"] == 0.5

    assert "ceo" in resolved.preferred_patterns
    assert "builder" in resolved.preferred_patterns

    assert resolved.scope["level"] == "org"
    assert resolved.scope["project"] == "alpha"
    print("  PASS: resolve_with_inheritance")


def test_resolve_without_parent():
    clear()
    p = BrainProfile(brain_id="solo", name="Solo")
    register(p)
    resolved = resolve_with_inheritance("solo")
    assert resolved is not None
    assert resolved.brain_id == "solo"
    print("  PASS: resolve_without_parent")


def test_resolve_nonexistent():
    clear()
    assert resolve_with_inheritance("nope") is None
    print("  PASS: resolve_nonexistent")


def test_ensure_default_brains():
    clear()
    created = ensure_default_brains()
    assert "system" in created
    assert "user" in created
    assert "claude_code" in created
    assert "workstation" in created

    assert get("system") is not None
    assert get("system").authority == AuthorityLevel.ADMIN
    assert get("claude_code").parent_brain_id == "system"

    created2 = ensure_default_brains()
    assert created2 == []
    print("  PASS: ensure_default_brains")


def test_ensure_default_brains_with_project():
    clear()
    created = ensure_default_brains({"name": "Initiate Arena"})
    assert "project" in created
    assert get("project").scope["name"] == "Initiate Arena"
    print("  PASS: ensure_default_brains_with_project")


def test_registry_singleton():
    r1 = get_brain_registry()
    r2 = get_brain_registry()
    assert r1 is r2

    clear()
    p = BrainProfile(brain_id="via_class", name="Via Class")
    r1.register(p)
    assert r1.get("via_class") is not None

    r1.reset()
    assert list_brains() == []
    print("  PASS: registry_singleton")


def test_registry_clear():
    clear()
    register(BrainProfile(brain_id="a", name="A"))
    register(BrainProfile(brain_id="b", name="B"))
    assert len(list_brains()) == 2
    clear()
    assert len(list_brains()) == 0
    print("  PASS: registry_clear")


# ─── BrainSignals ─────────────────────────────────────────────────


def test_signal_emit():
    clear_signals()
    sig = emit_signal("system", "startup", {"stage": "ambient"})
    assert sig.brain_id == "system"
    assert sig.signal_type == "startup"
    assert sig.payload["stage"] == "ambient"
    assert sig.signal_id.startswith("bsig_")
    assert sig.timestamp != ""
    print("  PASS: signal_emit")


def test_signal_list_by_brain():
    clear_signals()
    emit_signal("system", "startup")
    emit_signal("system", "correction")
    emit_signal("user", "input")

    sys_signals = list_signals("system")
    assert len(sys_signals) == 2

    usr_signals = list_signals("user")
    assert len(usr_signals) == 1
    print("  PASS: signal_list_by_brain")


def test_signal_list_by_type():
    clear_signals()
    emit_signal("system", "startup")
    emit_signal("system", "correction")
    emit_signal("user", "startup")

    startup_signals = list_signals("system", signal_type="startup")
    assert len(startup_signals) == 1
    assert startup_signals[0].signal_type == "startup"
    print("  PASS: signal_list_by_type")


def test_signal_targeting():
    clear_signals()
    emit_signal("system", "delegation", target_brain_id="claude_code")
    emit_signal("system", "observation")
    emit_signal("user", "directive", target_brain_id="claude_code")

    targeted = list_signals_for_target("claude_code")
    assert len(targeted) == 2

    targeted_typed = list_signals_for_target("claude_code", signal_type="delegation")
    assert len(targeted_typed) == 1
    print("  PASS: signal_targeting")


def test_signal_get_by_id():
    clear_signals()
    sig = emit_signal("system", "test")
    found = get_signal(sig.signal_id)
    assert found is not None
    assert found.signal_id == sig.signal_id

    assert get_signal("nonexistent") is None
    print("  PASS: signal_get_by_id")


def test_signal_count():
    clear_signals()
    emit_signal("a", "x")
    emit_signal("a", "y")
    emit_signal("b", "z")

    assert signal_count("a") == 2
    assert signal_count("b") == 1
    assert signal_count() == 3
    print("  PASS: signal_count")


def test_signal_all():
    clear_signals()
    emit_signal("a", "x")
    emit_signal("b", "y")
    emit_signal("c", "z")

    all_sigs = list_all_signals()
    assert len(all_sigs) == 3
    print("  PASS: signal_all")


def test_signal_newest_first():
    clear_signals()
    s1 = emit_signal("a", "first")
    s2 = emit_signal("a", "second")

    signals = list_signals("a")
    assert signals[0].signal_id == s2.signal_id
    assert signals[1].signal_id == s1.signal_id
    print("  PASS: signal_newest_first")


def test_signal_frozen():
    sig = emit_signal("a", "test")
    try:
        sig.brain_id = "modified"
        assert False, "Should have raised"
    except AttributeError:
        pass
    print("  PASS: signal_frozen")


def test_signal_serialization():
    clear_signals()
    sig = emit_signal("system", "test", {"key": "val"}, target_brain_id="user")
    d = sig.to_dict()
    assert d["brain_id"] == "system"
    assert d["signal_type"] == "test"
    assert d["payload"]["key"] == "val"
    assert d["target_brain_id"] == "user"

    serialized = json.dumps(d)
    assert '"signal_id"' in serialized
    print("  PASS: signal_serialization")


# ─── Boundary safety ──────────────────────────────────────────────


def test_no_execution_imports():
    """Brain modules must not import from execution, adapters, or runtime."""
    brain_dir = "/opt/OS/umh/brains/"
    forbidden_pattern = re.compile(
        r"^\s*(?:from|import)\s+(?:umh\.execution|umh\.adapters|umh\.runtime)",
    )

    for fname in os.listdir(brain_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(brain_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                assert not forbidden_pattern.match(line), (
                    f"Forbidden import in {fpath}:{i}: {line.strip()}"
                )
    print("  PASS: no_execution_imports")


def test_no_tool_calls():
    """Brain modules must not call tools or shell commands."""
    brain_dir = "/opt/OS/umh/brains/"
    forbidden = re.compile(
        r"\b(subprocess|os\.system|os\.popen|shutil\.rmtree)\b",
    )

    for fname in os.listdir(brain_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(brain_dir, fname)
        with open(fpath) as f:
            for i, line in enumerate(f, 1):
                if line.strip().startswith("#"):
                    continue
                assert not forbidden.search(line), f"Forbidden call in {fpath}:{i}: {line.strip()}"
    print("  PASS: no_tool_calls")


# ─── Runner ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Phase 11B — Substrate-Expression Protocol...")
    print()
    print("BrainProfile:")
    test_profile_creation()
    test_profile_validation()
    test_profile_frozen()
    test_profile_serialization()

    print()
    print("ExpressionState:")
    test_expression_amplify()
    test_expression_silence()
    test_expression_prefer_pattern()
    test_expression_clamping()
    test_expression_apply_correction()
    test_expression_correction_adds_timestamp()
    test_expression_inherit()
    test_expression_serialization()

    print()
    print("Registry:")
    test_registry_crud()
    test_registry_auto_expression_state()
    test_registry_explicit_expression_state()
    test_registry_update_expression()
    test_registry_apply_correction()
    test_registry_children()
    test_registry_create_child()
    test_registry_create_child_with_overrides()
    test_resolve_with_inheritance()
    test_resolve_without_parent()
    test_resolve_nonexistent()
    test_ensure_default_brains()
    test_ensure_default_brains_with_project()
    test_registry_singleton()
    test_registry_clear()

    print()
    print("Signals:")
    test_signal_emit()
    test_signal_list_by_brain()
    test_signal_list_by_type()
    test_signal_targeting()
    test_signal_get_by_id()
    test_signal_count()
    test_signal_all()
    test_signal_newest_first()
    test_signal_frozen()
    test_signal_serialization()

    print()
    print("Boundary Safety:")
    test_no_execution_imports()
    test_no_tool_calls()

    print()
    print("All Phase 11B tests passed.")
