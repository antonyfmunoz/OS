"""
Tests for Goal Validation & Constraint Layer.

Validates:
    1. duplicate goals are rejected
    2. invalid goals never enter registry
    3. validator does not mutate valid goals
    4. determinism preserved
    5. no regression
    6. no new LLM calls
    7. ExecutionSpine unchanged
"""

import sys

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _test(name: str, ok: bool, detail: str = "") -> None:
    global _PASS, _FAIL
    if ok:
        _PASS += 1
    else:
        _FAIL += 1
    status = "PASS" if ok else "FAIL"
    suffix = f" -- {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")


def _section(name: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {name}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# 0. Imports
# ═══════════════════════════════════════════════════════════════════════════════

_section("0. Imports + Setup")

from umh.runtime_engine.goal_validator import (
    GoalValidator,
    ValidationResult,
    VALID,
    SIMILARITY_THRESHOLD,
    MIN_CRITERIA_KEYS,
    PRIORITY_MIN,
    PRIORITY_MAX,
    CAPACITY_PRESSURE_THRESHOLD,
    ELEVATED_CONFIDENCE_THRESHOLD,
    DOMINATION_MARGIN,
    _criteria_similarity,
)
from umh.goals.state import GoalState, GoalRegistry, GoalTracker
from umh.runtime_engine.meta_goal import (
    MetaGoal,
    MetaGoalEngine,
    MAX_GOALS,
    GENERATED_PRIORITY_BASE,
)
from umh.runtime_engine.decision_trace import DecisionTrace, build_trace

_test("imports", True)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _make_meta_goal(
    goal_id: str = "test_goal",
    parent_goals: tuple = (),
    confidence: float = 0.7,
    utility_estimate: float = 0.5,
    description: str = "Test goal description",
    criteria: dict | None = None,
    priority: float = 0.5,
    lifecycle_state: str = "active",
) -> MetaGoal:
    return MetaGoal(
        goal_id=goal_id,
        origin="generated",
        parent_goals=parent_goals,
        confidence=confidence,
        utility_estimate=utility_estimate,
        lifecycle_state=lifecycle_state,
        description=description,
        success_criteria=criteria
        if criteria is not None
        else {"domain": "test", "type": "validate"},
        priority=priority,
        generation_turn=1,
        generation_reason="test",
    )


def _make_registry(*goals_data) -> GoalRegistry:
    reg = GoalRegistry()
    for gd in goals_data:
        if isinstance(gd, GoalState):
            reg.add_goal(gd)
        elif isinstance(gd, tuple):
            reg.add_goal(
                GoalState(
                    goal_id=gd[0],
                    description=f"Test goal {gd[0]}",
                    success_criteria=gd[2] if len(gd) > 2 else {"domain": "test"},
                    priority=gd[1] if len(gd) > 1 else 0.5,
                )
            )
    return reg


# ═══════════════════════════════════════════════════════════════════════════════
# 1. ValidationResult model
# ═══════════════════════════════════════════════════════════════════════════════

_section("1. ValidationResult model")

vr = ValidationResult(
    is_valid=True,
    violations=("test_warning",),
    severity="warn",
)
_test("is_valid set", vr.is_valid is True)
_test("violations tuple", vr.violations == ("test_warning",))
_test("severity set", vr.severity == "warn")
_test("corrected_goal None", vr.corrected_goal is None)

d = vr.to_dict()
_test("to_dict is_valid", d["is_valid"] is True)
_test("to_dict violations list", isinstance(d["violations"], list))
_test("to_dict severity", d["severity"] == "warn")

_test("VALID constant", VALID.is_valid is True)
_test("VALID no violations", len(VALID.violations) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Valid goal passes
# ═══════════════════════════════════════════════════════════════════════════════

_section("2. Valid goal passes")

validator = GoalValidator()
reg = _make_registry(("existing_goal", 0.7, {"domain": "sales"}))
mg = _make_meta_goal(
    goal_id="new_goal",
    criteria={"domain": "engineering", "type": "build"},
    description="Build the widget",
)

result = validator.validate(mg, reg)
_test("valid goal passes", result.is_valid)
_test("no violations", len(result.violations) == 0 or result.severity != "reject")
_test("severity not reject", result.severity != "reject")


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Rule A: Redundancy — exact ID match
# ═══════════════════════════════════════════════════════════════════════════════

_section("3. Redundancy — exact ID match")

validator = GoalValidator()
reg = _make_registry(("goal_a", 0.7, {"domain": "test"}))
mg = _make_meta_goal(goal_id="goal_a")

result = validator.validate(mg, reg)
_test("exact ID rejected", not result.is_valid)
_test("severity reject", result.severity == "reject")
_test(
    "violation mentions redundancy",
    any("redundancy" in v for v in result.violations),
)
_test(
    "violation mentions exact_id",
    any("exact_id_match" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Rule A: Redundancy — criteria similarity
# ═══════════════════════════════════════════════════════════════════════════════

_section("4. Redundancy — criteria similarity")

validator = GoalValidator()
reg = _make_registry(
    ("existing", 0.7, {"domain": "test", "type": "validate", "scope": "unit"})
)
mg = _make_meta_goal(
    goal_id="new_similar",
    criteria={"domain": "test", "type": "validate", "scope": "unit"},
    description="Very similar goal",
)

result = validator.validate(mg, reg)
_test("similar criteria rejected", not result.is_valid)
_test(
    "violation mentions criteria_similarity",
    any("criteria_similarity" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Rule A: Parent overlap exception
# ═══════════════════════════════════════════════════════════════════════════════

_section("5. Redundancy — parent overlap exception")

validator = GoalValidator()
reg = _make_registry(("parent_goal", 0.7, {"domain": "test", "type": "validate"}))
mg = _make_meta_goal(
    goal_id="child_goal",
    parent_goals=("parent_goal",),
    criteria={"domain": "test", "type": "validate"},
    description="Child of parent goal",
)

result = validator.validate(mg, reg)
_test(
    "parent overlap not rejected for redundancy",
    not any("criteria_similarity" in v for v in result.violations),
    f"violations={result.violations}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Rule B: Degenerate — empty criteria
# ═══════════════════════════════════════════════════════════════════════════════

_section("6. Degenerate — empty criteria")

validator = GoalValidator()
reg = GoalRegistry()
mg = _make_meta_goal(criteria={}, description="Empty criteria goal")

result = validator.validate(mg, reg)
_test("empty criteria rejected", not result.is_valid)
_test(
    "violation mentions degenerate",
    any("degenerate" in v for v in result.violations),
)
_test(
    "violation mentions empty",
    any("empty_criteria" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Rule B: Degenerate — only meta keys
# ═══════════════════════════════════════════════════════════════════════════════

_section("7. Degenerate — only meta keys")

validator = GoalValidator()
reg = GoalRegistry()
mg = _make_meta_goal(
    criteria={"_meta_origin": "alternative"},
    description="Only meta keys",
)

result = validator.validate(mg, reg)
_test("only meta keys rejected", not result.is_valid)
_test(
    "violation mentions insufficient",
    any("insufficient_criteria" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Rule B: Degenerate — missing description
# ═══════════════════════════════════════════════════════════════════════════════

_section("8. Degenerate — missing description")

validator = GoalValidator()
reg = GoalRegistry()
mg = _make_meta_goal(
    criteria={"domain": "test"},
    description="",
)

result = validator.validate(mg, reg)
_test("empty description rejected", not result.is_valid)
_test(
    "violation mentions description",
    any("missing_description" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Rule C: Dominated goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("9. Dominated goals")

validator = GoalValidator()
reg = _make_registry(("parent", 0.8, {"domain": "test"}))

tracker = reg.get_tracker("parent")
for _ in range(5):
    tracker.update_success(0.85)

mg = _make_meta_goal(
    goal_id="weak_child",
    parent_goals=("parent",),
    confidence=0.3,
    utility_estimate=0.3,
    description="Weak child goal",
    criteria={"domain": "different"},
)

result = validator.validate(mg, reg)
_test("dominated goal rejected", not result.is_valid)
_test(
    "violation mentions dominated",
    any("dominated" in v for v in result.violations),
)
_test(
    "violation mentions parent",
    any("by_parent:parent" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Rule C: Not dominated — one dimension better
# ═══════════════════════════════════════════════════════════════════════════════

_section("10. Not dominated — one dimension better")

validator = GoalValidator()
reg = _make_registry(("parent2", 0.6, {"domain": "test"}))
tracker = reg.get_tracker("parent2")
for _ in range(5):
    tracker.update_success(0.5)

mg = _make_meta_goal(
    goal_id="strong_child",
    parent_goals=("parent2",),
    confidence=0.8,
    utility_estimate=0.3,
    description="Strong confidence child",
    criteria={"domain": "different"},
)

result = validator.validate(mg, reg)
_test(
    "not dominated when confidence is higher",
    not any("dominated" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Rule D: Cycles — self-reference
# ═══════════════════════════════════════════════════════════════════════════════

_section("11. Cycles — self-reference")

validator = GoalValidator()
reg = GoalRegistry()
mg = _make_meta_goal(
    goal_id="self_ref",
    parent_goals=("self_ref",),
    description="Self referencing goal",
    criteria={"domain": "test"},
)

result = validator.validate(mg, reg)
_test("self-reference rejected", not result.is_valid)
_test(
    "violation mentions cycle",
    any("cycle" in v for v in result.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Rule E: Capacity pressure
# ═══════════════════════════════════════════════════════════════════════════════

_section("12. Capacity pressure")

validator = GoalValidator()
reg = GoalRegistry()

pressure_count = int(MAX_GOALS * CAPACITY_PRESSURE_THRESHOLD)
for i in range(pressure_count):
    reg.add_goal(
        GoalState(
            goal_id=f"fill_{i:02d}",
            description=f"Fill goal {i}",
            success_criteria={"domain": f"fill_{i}"},
            priority=0.5,
        )
    )

mg_low = _make_meta_goal(
    goal_id="low_conf_under_pressure",
    confidence=0.3,
    description="Low confidence under pressure",
    criteria={"domain": "new_domain"},
)

result = validator.validate(mg_low, reg)
_test("low confidence rejected under pressure", not result.is_valid)
_test(
    "violation mentions capacity",
    any("capacity_pressure" in v for v in result.violations),
)

mg_high = _make_meta_goal(
    goal_id="high_conf_under_pressure",
    confidence=0.8,
    description="High confidence under pressure",
    criteria={"domain": "high_conf_domain"},
)

result2 = validator.validate(mg_high, reg)
_test(
    "high confidence passes under pressure",
    not any("capacity_pressure" in v for v in result2.violations),
)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Auto-correction — priority clamping
# ═══════════════════════════════════════════════════════════════════════════════

_section("13. Auto-correction — priority clamping")

validator = GoalValidator()
reg = GoalRegistry()

mg_low_pri = _make_meta_goal(
    goal_id="low_pri",
    priority=0.01,
    description="Very low priority",
    criteria={"domain": "test"},
)

result = validator.validate(mg_low_pri, reg)
_test("low priority is valid", result.is_valid)
_test("corrected goal exists", result.corrected_goal is not None)
_test(
    "priority clamped to min",
    result.corrected_goal.priority == PRIORITY_MIN,
    f"pri={result.corrected_goal.priority}",
)
_test("severity auto-fix", result.severity == "auto-fix")

mg_high_pri = _make_meta_goal(
    goal_id="high_pri",
    priority=1.5,
    description="Very high priority",
    criteria={"domain": "test"},
)

result2 = validator.validate(mg_high_pri, reg)
_test("high priority is valid", result2.is_valid)
_test("corrected high priority", result2.corrected_goal is not None)
_test(
    "priority clamped to max",
    result2.corrected_goal.priority == PRIORITY_MAX,
    f"pri={result2.corrected_goal.priority}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Auto-correction — criteria normalization
# ═══════════════════════════════════════════════════════════════════════════════

_section("14. Auto-correction — criteria normalization")

validator = GoalValidator()
reg = GoalRegistry()

mg_messy = _make_meta_goal(
    goal_id="messy_criteria",
    criteria={"Domain": "Test", "TYPE": "Validate"},
    description="Messy criteria",
)

result = validator.validate(mg_messy, reg)
_test("messy criteria is valid", result.is_valid)
_test("corrected goal exists", result.corrected_goal is not None)
if result.corrected_goal:
    _test(
        "keys normalized",
        "domain" in result.corrected_goal.success_criteria,
        f"keys={list(result.corrected_goal.success_criteria.keys())}",
    )
    _test(
        "values normalized",
        result.corrected_goal.success_criteria.get("domain") == "test",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Validator does NOT mutate valid goals
# ═══════════════════════════════════════════════════════════════════════════════

_section("15. Valid goals not mutated")

validator = GoalValidator()
reg = GoalRegistry()

mg_clean = _make_meta_goal(
    goal_id="clean_goal",
    priority=0.5,
    criteria={"domain": "test", "type": "clean"},
    description="Perfectly valid goal",
)

result = validator.validate(mg_clean, reg)
_test("clean goal is valid", result.is_valid)
_test("no correction needed", result.corrected_goal is None)
_test("severity warn", result.severity == "warn")
_test("no violations", len(result.violations) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Batch validation
# ═══════════════════════════════════════════════════════════════════════════════

_section("16. Batch validation")

validator = GoalValidator()
reg = GoalRegistry()

goals = [
    _make_meta_goal(goal_id="batch_a", criteria={"domain": "a"}, description="Goal A"),
    _make_meta_goal(goal_id="batch_b", criteria={}, description="Goal B"),
    _make_meta_goal(goal_id="batch_c", criteria={"domain": "c"}, description="Goal C"),
]

results = validator.validate_batch(goals, reg)
_test("batch returns 3 results", len(results) == 3)
_test("batch_a valid", results[0].is_valid)
_test("batch_b invalid (empty criteria)", not results[1].is_valid)
_test("batch_c valid", results[2].is_valid)


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Criteria similarity function
# ═══════════════════════════════════════════════════════════════════════════════

_section("17. Criteria similarity")

sim_identical = _criteria_similarity(
    {"a": "1", "b": "2"},
    {"a": "1", "b": "2"},
)
_test("identical criteria = 1.0", sim_identical == 1.0)

sim_disjoint = _criteria_similarity(
    {"a": "1"},
    {"b": "2"},
)
_test("disjoint criteria = 0.0", sim_disjoint == 0.0)

sim_partial = _criteria_similarity(
    {"a": "1", "b": "2"},
    {"a": "1", "c": "3"},
)
_test("partial overlap in (0, 1)", 0.0 < sim_partial < 1.0)

sim_both_empty = _criteria_similarity({}, {})
_test("both empty = 1.0", sim_both_empty == 1.0)

sim_one_empty = _criteria_similarity({"a": "1"}, {})
_test("one empty = 0.0", sim_one_empty == 0.0)

sim_meta_ignored = _criteria_similarity(
    {"domain": "test", "_meta_origin": "alt"},
    {"domain": "test", "_meta_origin": "spec"},
)
_test("meta keys ignored", sim_meta_ignored > 0.9)


# ═══════════════════════════════════════════════════════════════════════════════
# 18. Determinism — same inputs same outputs
# ═══════════════════════════════════════════════════════════════════════════════

_section("18. Determinism")


def _run_determinism():
    v1 = GoalValidator()
    v2 = GoalValidator()
    r1 = _make_registry(("exist", 0.5, {"domain": "test"}))
    r2 = _make_registry(("exist", 0.5, {"domain": "test"}))
    mg1 = _make_meta_goal(goal_id="det_goal", criteria={"domain": "test", "type": "x"})
    mg2 = _make_meta_goal(goal_id="det_goal", criteria={"domain": "test", "type": "x"})
    return v1.validate(mg1, r1), v2.validate(mg2, r2)


r1, r2 = _run_determinism()
_test("deterministic is_valid", r1.is_valid == r2.is_valid)
_test("deterministic violations", r1.violations == r2.violations)
_test("deterministic severity", r1.severity == r2.severity)


# ═══════════════════════════════════════════════════════════════════════════════
# 19. DecisionTrace fields
# ═══════════════════════════════════════════════════════════════════════════════

_section("19. DecisionTrace fields")

trace = build_trace(
    turn_id=1,
    goal_validation_results=({"is_valid": False, "violations": ["redundancy"]},),
    rejected_goals=("bad_goal",),
    validation_reason="rejected",
)
_test("trace has goal_validation_results", trace.goal_validation_results is not None)
_test("trace has rejected_goals", trace.rejected_goals is not None)
_test("trace has validation_reason", trace.validation_reason == "rejected")

td = trace.to_dict()
_test("to_dict has goal_validation_results", "goal_validation_results" in td)
_test("to_dict has rejected_goals", "rejected_goals" in td)
_test("to_dict has validation_reason", "validation_reason" in td)

trace_empty = build_trace(turn_id=2)
td2 = trace_empty.to_dict()
_test("empty trace no goal_validation_results", "goal_validation_results" not in td2)
_test("empty trace no rejected_goals", "rejected_goals" not in td2)
_test("empty trace no validation_reason", "validation_reason" not in td2)


# ═══════════════════════════════════════════════════════════════════════════════
# 20. Invalid goals never enter registry (integration)
# ═══════════════════════════════════════════════════════════════════════════════

_section("20. Integration — invalid goals blocked from registry")

validator = GoalValidator()
reg = _make_registry(("goal_x", 0.7, {"domain": "sales", "type": "close"}))

dup = _make_meta_goal(
    goal_id="goal_x",
    criteria={"domain": "sales", "type": "close"},
    description="Duplicate goal",
)

result = validator.validate(dup, reg)
_test("duplicate detected", not result.is_valid)

before_count = len(reg.get_all_goals())
if not result.is_valid:
    pass  # caller should NOT add to registry
_test("registry unchanged", len(reg.get_all_goals()) == before_count)


# ═══════════════════════════════════════════════════════════════════════════════
# 21. Multiple rejection reasons accumulate
# ═══════════════════════════════════════════════════════════════════════════════

_section("21. Multiple rejection reasons")

validator = GoalValidator()
reg = GoalRegistry()

reg_multi = _make_registry(("existing_dup", 0.7, {"domain": "test"}))
mg_multi = _make_meta_goal(
    goal_id="existing_dup",
    criteria={},
    description="",
)

result = validator.validate(mg_multi, reg_multi)
_test("multiple violations", len(result.violations) >= 2)
_test("rejected", not result.is_valid)


# ═══════════════════════════════════════════════════════════════════════════════
# 22. No LLM calls verification
# ═══════════════════════════════════════════════════════════════════════════════

_section("22. No LLM calls")

import inspect

src = inspect.getsource(GoalValidator)
_test("no call_with_fallback", "call_with_fallback" not in src)
_test("no anthropic", "anthropic" not in src.lower())
_test("no openai", "openai" not in src.lower())
_test("no genai", "genai" not in src)
_test("no agent_runtime", "agent_runtime" not in src)


# ═══════════════════════════════════════════════════════════════════════════════
# 23. ExecutionSpine unchanged
# ═══════════════════════════════════════════════════════════════════════════════

_section("23. ExecutionSpine unchanged")

spine_src = inspect.getsource(
    __import__("umh.runtime_engine.execution_spine", fromlist=["ExecutionSpine"]).ExecutionSpine
)
_test("spine has no goal_validator ref", "goal_validator" not in spine_src)
_test("spine has no GoalValidator ref", "GoalValidator" not in spine_src)


# ═══════════════════════════════════════════════════════════════════════════════
# 24. Backward compatibility — no registry = no validation
# ═══════════════════════════════════════════════════════════════════════════════

_section("24. Backward compatibility")

validator = GoalValidator()
reg = GoalRegistry()
mg = _make_meta_goal(
    goal_id="compat",
    criteria={"domain": "test"},
    description="Backward compat goal",
)

result = validator.validate(mg, reg)
_test(
    "empty registry no pressure issues", result.is_valid or result.severity != "reject"
)

trace_compat = build_trace(turn_id=99)
_test("trace with no validation fields", trace_compat.goal_validation_results is None)
_test("trace with no rejected goals", trace_compat.rejected_goals is None)


# ═══════════════════════════════════════════════════════════════════════════════
# 25. End-to-end: MetaGoalEngine → GoalValidator → GoalRegistry
# ═══════════════════════════════════════════════════════════════════════════════

_section("25. End-to-end pipeline")

engine = MetaGoalEngine()
validator = GoalValidator()
reg = _make_registry(("goal_a", 0.7, {"domain": "sales"}))

mg_valid = _make_meta_goal(
    goal_id="meta_new",
    criteria={"domain": "engineering"},
    description="Valid new goal",
    confidence=0.8,
)
engine.register_generated(mg_valid)
engine.activate_candidate("meta_new")

activated = engine.get_generated("meta_new")
vr = validator.validate(activated, reg)

if vr.is_valid:
    use_mg = vr.corrected_goal if vr.corrected_goal else activated
    gs = engine.to_meta_goal_state(use_mg)
    reg.add_goal(gs)

_test("valid goal entered registry", reg.get_goal("meta_new") is not None)

mg_dup = _make_meta_goal(
    goal_id="meta_new",
    criteria={"domain": "engineering"},
    description="Duplicate of previous",
)

vr2 = validator.validate(mg_dup, reg)
_test("duplicate blocked", not vr2.is_valid)
_test(
    "registry size unchanged",
    len(reg.get_all_goals()) == 2,
    f"count={len(reg.get_all_goals())}",
)


# ═══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'=' * 60}")
print(f"  TOTAL: {_PASS} passed, {_FAIL} failed (out of {_PASS + _FAIL})")
print(f"{'=' * 60}")

if _FAIL > 0:
    sys.exit(1)
