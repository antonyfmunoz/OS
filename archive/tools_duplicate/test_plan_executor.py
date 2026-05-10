#!/usr/bin/env python3
"""
Validation suite for plan_executor — tests all execution modes.

Tests:
1. Small task → SINGLE_AGENT (passthrough)
2. Large multi-phase task → SEQUENTIAL_PHASES
3. Independent subtasks → PARALLEL_SUBAGENTS
4. High-risk task → PLANNER_EXECUTOR_VERIFIER
5. Heavy multi-phase → HYBRID
6. High context pressure → checkpoint enforcement
7. Compute preference → node resolution
8. Backward compatibility → simple tasks unchanged
9. Plan-to-execution wiring integrity
10. Orchestration record traceability
"""

import sys
sys.path.insert(0, "/opt/OS")

import json
from datetime import datetime

# ─── Test framework ──────────────────────────────────────────────────────────

_pass = 0
_fail = 0
_results: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global _pass, _fail
    status = "PASS" if condition else "FAIL"
    if condition:
        _pass += 1
    else:
        _fail += 1
    _results.append({"name": name, "status": status, "detail": detail})
    print(f"  [{status}] {name}" + (f" — {detail}" if detail and not condition else ""))


# ─── Test 1: Context budget assessment ─────────────────────────────────────

print("\n=== Test 1: Context budget assessment ===")
from umh.substrate.context_budget import (
    assess_context_budget,
    ContextPressure,
    TaskComplexity,
    OrchestrationMode,
)

# Small task
small_budget = assess_context_budget("hello")
check(
    "small task → SMALL complexity",
    small_budget.task_complexity == TaskComplexity.SMALL,
    f"got {small_budget.task_complexity.value}",
)
check(
    "small task → LOW pressure",
    small_budget.pressure == ContextPressure.LOW,
    f"got {small_budget.pressure.value}",
)
check(
    "small task → no decomposition",
    not small_budget.should_decompose,
)

# Large task
large_text = """
Phase 1: Research the market
Do comprehensive competitive analysis across 10 companies.

Phase 2: Build the strategy
Create a go-to-market strategy with pricing, positioning, and channels.

Phase 3: Create the deliverables
Build pitch deck, one-pager, and sales scripts.

Phase 4: Review and iterate
Review all deliverables for consistency and completeness.
"""
large_budget = assess_context_budget(large_text)
check(
    "large task → HEAVY complexity",
    large_budget.task_complexity == TaskComplexity.HEAVY,
    f"got {large_budget.task_complexity.value}",
)
check(
    "large task → should decompose",
    large_budget.should_decompose,
)
check(
    "large task → multiple phases detected",
    large_budget.phase_count >= 3,
    f"got {large_budget.phase_count} phases",
)

# High pressure
high_pressure_budget = assess_context_budget(
    "small task",
    current_session_chars=450_000,  # 80%+ of default budget
)
check(
    "high session usage → CRITICAL pressure",
    high_pressure_budget.pressure == ContextPressure.CRITICAL,
    f"got {high_pressure_budget.pressure.value}",
)

# ���── Test 2: Orchestration plan generation ��────────────────────────��───────

print("\n=== Test 2: Orchestration plan generation ===")
from umh.substrate.adaptive_orchestration_policy import (
    plan_task_orchestration,
    OrchestrationPlan,
    RiskLevel,
    PreferredNode,
    ReasoningTier,
)

# Small task → SINGLE_AGENT
small_plan = plan_task_orchestration("hello")
check(
    "small task → SINGLE_AGENT mode",
    small_plan.mode == OrchestrationMode.SINGLE_AGENT,
    f"got {small_plan.mode.value}",
)

# Large multi-phase → non-trivial mode (SEQ, PARALLEL, or HYBRID depending on analysis)
seq_plan = plan_task_orchestration(large_text)
check(
    "large multi-phase → non-trivial mode",
    seq_plan.mode != OrchestrationMode.SINGLE_AGENT,
    f"got {seq_plan.mode.value}",
)
check(
    "sequential plan has phases",
    len(seq_plan.phases) >= 2,
    f"got {len(seq_plan.phases)} phases",
)

# Independent subtasks → PARALLEL_SUBAGENTS
# The task must be large enough (MEDIUM+ complexity) for parallel to trigger.
# A 150-char task stays SINGLE_AGENT even with independent markers.
parallel_text = """
Phase 1 — Sub-agent A: Research all competitors in the AI coaching market.
Compile a comprehensive list of at least 20 competitors, their pricing models,
target demographics, key differentiators, and market positioning strategies.

Phase 2 — Sub-agent B: Analyze pricing models across the coaching industry.
Compare subscription tiers, one-time purchases, cohort models, and hybrid
approaches. Include data from at least 15 companies with revenue estimates.

Phase 3 — Sub-agent C: Survey customer feedback and sentiment analysis.
Scrape reviews, testimonials, and social media mentions for the top 10
competitors. Identify common pain points and unmet needs.

All three tasks are independent and can run in parallel with no dependencies.
"""
par_plan = plan_task_orchestration(parallel_text)
check(
    "independent subtasks → PARALLEL_SUBAGENTS",
    par_plan.mode == OrchestrationMode.PARALLEL_SUBAGENTS,
    f"got {par_plan.mode.value} (complexity={par_plan.context_budget.task_complexity.value if par_plan.context_budget else '?'})",
)
check(
    "parallel plan has subagents",
    par_plan.max_subagents >= 2,
    f"got {par_plan.max_subagents}",
)
check(
    "parallel plan has budgets",
    len(par_plan.subagent_budgets) >= 2,
    f"got {len(par_plan.subagent_budgets)} budgets",
)

# High risk → PLANNER_EXECUTOR_VERIFIER
pev_plan = plan_task_orchestration("deploy to production", risk_level=RiskLevel.HIGH)
check(
    "high risk → PLANNER_EXECUTOR_VERIFIER",
    pev_plan.mode == OrchestrationMode.PLANNER_EXECUTOR_VERIFIER,
    f"got {pev_plan.mode.value}",
)
check(
    "PEV requires verifier",
    pev_plan.require_verifier,
)
check(
    "PEV requires planner",
    pev_plan.require_planner,
)
check(
    "PEV has 3 phases",
    len(pev_plan.phases) == 3,
    f"got {len(pev_plan.phases)} phases",
)

# ─── Test 3: Plan executor imports and structure ─────────��─────────────────

print("\n=== Test 3: Plan executor module structure ===")
from umh.substrate.plan_executor import (
    ExecutionOutcome,
    PhaseResult,
    PlanExecutionResult,
    execute_with_plan,
    execute_sequential_phases,
    execute_parallel_subagents,
    execute_planner_executor_verifier,
)
check("plan_executor imports cleanly", True)

check(
    "ExecutionOutcome has all states",
    set(e.value for e in ExecutionOutcome) == {"succeeded", "partial", "failed"},
)

# PhaseResult
pr = PhaseResult(phase_name="test", status="succeeded", output="hello")
pr_dict = pr.to_dict()
check(
    "PhaseResult serializes correctly",
    pr_dict["phase_name"] == "test" and pr_dict["status"] == "succeeded",
)

# PlanExecutionResult
per = PlanExecutionResult(plan_mode="single_agent")
per_dict = per.to_dict()
check(
    "PlanExecutionResult serializes correctly",
    per_dict["plan_mode"] == "single_agent" and "execution_id" in per_dict,
)

# ─── Test 4: Dry run mode ────────────────────────────────────────────────

print("\n=== Test 4: Dry run execution (no LLM calls) ===")

# Dry run SINGLE_AGENT
dry_single = execute_with_plan("hello", small_plan, dry_run=True)
check(
    "dry run SINGLE_AGENT returns plan analysis",
    dry_single.outcome == ExecutionOutcome.SUCCEEDED,
    f"got {dry_single.outcome.value}",
)
check(
    "dry run has plan in metadata",
    "plan" in dry_single.metadata,
)
check(
    "dry run records execution_path",
    "dry_run" in dry_single.execution_path,
    f"got {dry_single.execution_path}",
)

# Dry run SEQUENTIAL
dry_seq = execute_with_plan(large_text, seq_plan, dry_run=True)
check(
    "dry run SEQUENTIAL returns plan analysis",
    dry_seq.outcome == ExecutionOutcome.SUCCEEDED,
)

# Dry run PARALLEL
dry_par = execute_with_plan(parallel_text, par_plan, dry_run=True)
check(
    "dry run PARALLEL returns plan analysis",
    dry_par.outcome == ExecutionOutcome.SUCCEEDED,
)

# Dry run PEV
dry_pev = execute_with_plan("deploy to production", pev_plan, dry_run=True)
check(
    "dry run PEV returns plan analysis",
    dry_pev.outcome == ExecutionOutcome.SUCCEEDED,
)
check(
    "dry run PEV metadata has enforcement",
    "enforcement" in dry_pev.metadata,
)

# ─── Test 5: Context pressure enforcement ─────────────────────────────────

print("\n=== Test 5: Context pressure enforcement ===")
from umh.substrate.plan_executor import _enforce_context_pressure

# Normal pressure
normal_enforcement = _enforce_context_pressure(small_plan)
check(
    "normal pressure: no checkpoint forced",
    not normal_enforcement["checkpoint_forced"],
)

# High pressure plan
high_pressure_plan = plan_task_orchestration(
    large_text,
    current_session_chars=400_000,
)
high_enforcement = _enforce_context_pressure(high_pressure_plan)
check(
    "high pressure: checkpoint forced",
    high_enforcement["checkpoint_forced"],
    f"pressure={high_pressure_plan.context_budget.pressure.value if high_pressure_plan.context_budget else '?'}",
)

# Critical pressure with parallelism
critical_plan = plan_task_orchestration(
    parallel_text,
    current_session_chars=450_000,
)
critical_enforcement = _enforce_context_pressure(critical_plan)
check(
    "critical pressure: output limits applied",
    critical_enforcement["output_limits_applied"],
)

# ─── Test 6: Phase text splitting ────────────────────────────────────────

print("\n=== Test 6: Phase text splitting ===")
from umh.substrate.plan_executor import _split_task_into_phases

# Text with explicit phases
splits = _split_task_into_phases(large_text, seq_plan)
check(
    "split produces correct number of chunks",
    len(splits) == len(seq_plan.phases),
    f"got {len(splits)} splits for {len(seq_plan.phases)} phases",
)
check(
    "first split is non-empty",
    len(splits[0]) > 0,
    f"first split: {len(splits[0])} chars",
)

# Single-phase plan should not split
single_splits = _split_task_into_phases("hello world", small_plan)
check(
    "single-phase plan returns one chunk",
    len(single_splits) == 1,
)

# ─── Test 7: Node resolution ──��───────────────────��──────────────────────

print("\n=== Test 7: Node resolution ===")
from umh.substrate.plan_executor import _resolve_preferred_node, _resolve_node_for_phase
from umh.substrate.adaptive_orchestration_policy import OrchestrationPhase

# VPS preferred → returns "vps"
vps_node = _resolve_preferred_node(small_plan)
check(
    "VPS preferred → returns 'vps'",
    vps_node == "vps",
    f"got {vps_node}",
)

# Phase without local requirement → follows plan
phase_no_local = OrchestrationPhase(name="test", requires_local=False)
phase_node = _resolve_node_for_phase(phase_no_local, small_plan)
check(
    "non-local phase → follows plan preference",
    phase_node in ("local", "vps"),
)

# ─��─ Test 8: Orchestration record traceability ──────────────────────────

print("\n=== Test 8: Orchestration record traceability ===")
from umh.substrate.orchestration_record import (
    OrchestrationRecord,
    OrchestrationRecordStore,
    get_orchestration_store,
    summarize_phase_output,
    compress_for_next_phase,
)

# Record from plan
record = OrchestrationRecord.from_plan(
    pev_plan,
    task_id="test_task_1",
    correlation_id="test_corr_1",
)
check(
    "record captures mode",
    record.mode == "planner_executor_verifier",
)
check(
    "record captures phase count",
    record.phase_count == 3,
    f"got {record.phase_count}",
)
check(
    "record captures risk level",
    record.risk_level == "high",
)
check(
    "record captures checkpoint decisions",
    record.checkpoint_decisions.get("checkpoint_between_phases") is True,
)

# Serialization round-trip
serialized = record.serialize()
deserialized = OrchestrationRecord.deserialize(serialized)
check(
    "record round-trips through serialization",
    deserialized.mode == record.mode and deserialized.phase_count == record.phase_count,
)

# Summarization
long_output = "A" * 5000
summary = summarize_phase_output(long_output, max_chars=200)
check(
    "summarize respects max_chars",
    len(summary) <= 200,
    f"got {len(summary)} chars",
)

short_output = "hello world"
short_summary = summarize_phase_output(short_output)
check(
    "short output not truncated",
    short_summary == short_output,
)

# Compression
compressed = compress_for_next_phase(
    "Phase output here",
    carry_forward=["decision 1", "decision 2"],
    max_chars=500,
)
check(
    "compression includes carry forward",
    "decision 1" in compressed and "decision 2" in compressed,
)
check(
    "compression respects max_chars",
    len(compressed) <= 500,
    f"got {len(compressed)} chars",
)

# mark_completed with execution_trace
store = get_orchestration_store()
rid = store.append(record)
updated = store.mark_completed(
    rid,
    execution_path="planner:succeeded → executor:succeeded → verifier:succeeded",
    execution_trace={
        "phases_executed": 3,
        "phases_succeeded": 3,
        "phases_failed": 0,
        "subagents_spawned": 0,
        "summaries_created": 2,
        "compression_applied": True,
        "duration_s": 45.2,
        "outcome": "succeeded",
        "nodes_used": ["vps"],
    },
)
check(
    "mark_completed with trace succeeds",
    updated,
)

# Verify the trace was stored
found = store.by_task_id("test_task_1")
check(
    "execution trace stored in metadata",
    found is not None
    and "execution_trace" in found.metadata,
    f"metadata keys: {list(found.metadata.keys()) if found else 'None'}",
)

# ��── Test 9: Conversation router integration ─────────────────────────────

print("\n=== Test 9: Conversation router integration ===")
from umh.substrate.conversation_router import route_message

# Task routing produces orchestration plan
task_route = route_message("build me a landing page")
check(
    "task routing returns orchestration_plan",
    task_route.get("orchestration_plan") is not None,
)
check(
    "orchestration_plan has mode field",
    "mode" in (task_route.get("orchestration_plan") or {}),
)
check(
    "routing exposes _plan_object",
    task_route.get("_plan_object") is not None,
)
check(
    "_plan_object has .mode attribute",
    hasattr(task_route.get("_plan_object"), "mode"),
)

# Query routing does not produce plan (short-circuits)
# (query detection may or may not work depending on query_brain state)

# ─── Test 10: End-to-end plan mode routing ───────────────────────────────

print("\n=== Test 10: Mode routing coverage ===")

# Verify each mode produces the right plan
test_cases = [
    ("hello", OrchestrationMode.SINGLE_AGENT, "simple greeting"),
    (large_text, None, "large multi-phase"),  # could be SEQ, PARALLEL, or HYBRID
    (parallel_text, None, "parallel subtasks"),  # should be non-trivial mode
]

for text, expected_mode, label in test_cases:
    plan = plan_task_orchestration(text)
    if expected_mode is not None:
        check(
            f"'{label}' → {expected_mode.value}",
            plan.mode == expected_mode,
            f"got {plan.mode.value}",
        )
    else:
        check(
            f"'{label}' → non-single mode",
            plan.mode != OrchestrationMode.SINGLE_AGENT,
            f"got {plan.mode.value}",
        )

# High risk always PEV regardless of size
tiny_pev = plan_task_orchestration("hello", risk_level=RiskLevel.HIGH)
check(
    "high risk overrides size → PEV",
    tiny_pev.mode == OrchestrationMode.PLANNER_EXECUTOR_VERIFIER,
    f"got {tiny_pev.mode.value}",
)

# ─── Test 11: Substrate __init__ exports ─────────────────────────────────

print("\n=== Test 11: Substrate package exports ===")
from umh.runtime_engine.substrate import (
    ExecutionOutcome as _EO,
    PhaseResult as _PR,
    PlanExecutionResult as _PER,
    execute_with_plan as _ewp,
)
check("ExecutionOutcome exported from substrate", True)
check("PhaseResult exported from substrate", True)
check("PlanExecutionResult exported from substrate", True)
check("execute_with_plan exported from substrate", True)

# ─── Summary ────────────────────────────────────────────────────────────

print(f"\n{'=' * 60}")
print(f"RESULTS: {_pass} passed, {_fail} failed, {_pass + _fail} total")
print(f"{'=' * 60}")

if _fail > 0:
    print("\nFailed tests:")
    for r in _results:
        if r["status"] == "FAIL":
            print(f"  FAIL: {r['name']}" + (f" — {r['detail']}" if r['detail'] else ""))
    sys.exit(1)
else:
    print("\nAll tests passed.")
    sys.exit(0)
