#!/usr/bin/env python3
"""
Validation tests for context-budget-aware orchestration.

Covers all 9 scenarios from the specification:
1. Small low-pressure → SINGLE_AGENT
2. Medium task + moderate pressure → SEQUENTIAL_PHASES
3. Independent multi-part + compute → PARALLEL_SUBAGENTS
4. High-risk task → PLANNER_EXECUTOR_VERIFIER
5. Large task + constrained compute → SEQUENTIAL (not wide fanout)
6. Critical pressure → checkpoint/summarization required
7. Traceability record written correctly
8. Backward compatibility → existing tasks still work
9. Compute-aware preferences → local/VPS reflected
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, "/opt/OS")

_PASS = 0
_FAIL = 0


def _assert(condition: bool, label: str, detail: str = "") -> None:
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓ {label}")
    else:
        _FAIL += 1
        extra = f" — {detail}" if detail else ""
        print(f"  ✗ {label}{extra}")


# ── Imports ─────────────────────────────────────────────────────────────────

from umh.substrate.context_budget import (
    ContextBudget,
    ContextPressure,
    OrchestrationMode,
    TaskComplexity,
    allocate_subagent_budgets,
    assess_context_budget,
    detect_independent_subtasks,
    estimate_context_pressure,
    estimate_task_complexity,
    estimate_work_chars,
    should_checkpoint_now,
    should_decompose_task,
    should_force_summary,
)
from umh.substrate.adaptive_orchestration_policy import (
    AvailableCompute,
    OrchestrationPlan,
    PreferredNode,
    ReasoningTier,
    RiskLevel,
    decide_execution_shape,
    plan_task_orchestration,
)
from umh.substrate.orchestration_record import (
    OrchestrationRecord,
    OrchestrationRecordStore,
    compress_for_next_phase,
    summarize_phase_output,
)

print("=" * 60)
print("ADAPTIVE ORCHESTRATION VALIDATION TESTS")
print("=" * 60)


# ── Test 1: Small low-pressure → SINGLE_AGENT ──────────────────────────────
print("\n1. Small task + low pressure → SINGLE_AGENT")

budget_1 = assess_context_budget(
    "check the status of the deploy",
    current_session_chars=10_000,
)
_assert(budget_1.task_complexity == TaskComplexity.SMALL, "complexity is SMALL")
_assert(budget_1.pressure == ContextPressure.LOW, "pressure is LOW")
_assert(not budget_1.should_decompose, "should NOT decompose")

plan_1 = decide_execution_shape(
    task_text="check the status of the deploy",
    context_budget=budget_1,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(),
)
_assert(plan_1.mode == OrchestrationMode.SINGLE_AGENT, "mode is SINGLE_AGENT")
_assert(plan_1.reasoning_tier == ReasoningTier.LIGHT, "reasoning tier is LIGHT")
_assert(plan_1.rationale == "small_task_low_pressure", f"rationale: {plan_1.rationale}")


# ── Test 2: Medium task + moderate/high pressure → SEQUENTIAL_PHASES ───────
print("\n2. Medium task + high pressure → SEQUENTIAL_PHASES")

medium_task = (
    "Phase 1: Research the competitor landscape\n"
    "Phase 2: Create a comparison document\n"
    "Make it thorough but concise."
)
budget_2 = assess_context_budget(
    medium_task,
    current_session_chars=350_000,  # 62.5% of 560K budget → HIGH
)
_assert(
    budget_2.pressure == ContextPressure.HIGH,
    f"pressure is HIGH (got {budget_2.pressure.value})",
)
_assert(
    budget_2.task_complexity in (TaskComplexity.MEDIUM, TaskComplexity.LARGE),
    f"complexity is MEDIUM or LARGE (got {budget_2.task_complexity.value})",
)

plan_2 = decide_execution_shape(
    task_text=medium_task,
    context_budget=budget_2,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(),
)
_assert(
    plan_2.mode == OrchestrationMode.SEQUENTIAL_PHASES,
    f"mode is SEQUENTIAL_PHASES (got {plan_2.mode.value})",
)
_assert(plan_2.require_checkpoint_between_phases, "checkpoint between phases")


# ── Test 3: Independent multi-part + compute → PARALLEL_SUBAGENTS ──────────
print("\n3. Independent multi-part task + compute → PARALLEL_SUBAGENTS")

parallel_task = """
Sub-agent A — audit the authentication module thoroughly, checking token refresh,
session handling, OAuth integration, and password hashing implementations.

Sub-agent B — audit the payment module end to end, reviewing Stripe integration,
subscription handling, refund flows, and webhook processing logic.

Sub-agent C — audit the notification module, verifying email templates, push
notification delivery, SMS gateway integration, and rate limiting.

Each sub-agent can work independently in parallel. Merge results at the end.
The three audits cover completely separate domains with no shared state.
"""

budget_3 = assess_context_budget(
    parallel_task,
    current_session_chars=50_000,
)
_assert(detect_independent_subtasks(parallel_task), "detects independent subtasks")
_assert(budget_3.has_independent_subtasks, "budget marks independent subtasks")

plan_3 = decide_execution_shape(
    task_text=parallel_task,
    context_budget=budget_3,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(can_parallelize=True, max_parallel_agents=4),
)
_assert(
    plan_3.mode == OrchestrationMode.PARALLEL_SUBAGENTS,
    f"mode is PARALLEL_SUBAGENTS (got {plan_3.mode.value})",
)
_assert(plan_3.use_parallelism, "use_parallelism is True")
_assert(plan_3.max_subagents >= 2, f"at least 2 subagents (got {plan_3.max_subagents})")
_assert(len(plan_3.subagent_budgets) >= 2, "subagent budgets allocated")
_assert(plan_3.require_summary_between_phases, "summaries required (parallel merge)")


# ── Test 4: High-risk → PLANNER_EXECUTOR_VERIFIER ──────────────────────────
print("\n4. High-risk task → PLANNER_EXECUTOR_VERIFIER")

budget_4 = assess_context_budget(
    "deploy the new database schema migration to production",
    current_session_chars=100_000,
)
plan_4 = decide_execution_shape(
    task_text="deploy the new database schema migration to production",
    context_budget=budget_4,
    risk_level=RiskLevel.HIGH,
    available_compute=AvailableCompute(),
)
_assert(
    plan_4.mode == OrchestrationMode.PLANNER_EXECUTOR_VERIFIER,
    f"mode is PLANNER_EXECUTOR_VERIFIER (got {plan_4.mode.value})",
)
_assert(plan_4.require_verifier, "verifier required")
_assert(plan_4.require_planner, "planner required")
_assert(plan_4.require_checkpoint_between_phases, "checkpoint between phases")
_assert(
    plan_4.reasoning_tier == ReasoningTier.HEAVY,
    f"reasoning tier HEAVY (got {plan_4.reasoning_tier.value})",
)

# Verify 3 phases: plan → execute → verify
phase_names = [p.name for p in plan_4.phases]
_assert("plan" in phase_names, "has plan phase")
_assert("execute" in phase_names, "has execute phase")
_assert("verify" in phase_names, "has verify phase")


# ── Test 5: Large task + constrained compute → SEQUENTIAL ──────────────────
print("\n5. Large task + constrained compute → SEQUENTIAL (not wide fanout)")

large_task = (
    """
Phase 1: Audit the authentication system
Phase 2: Redesign the token refresh flow
Phase 3: Implement the new token handler
Phase 4: Write integration tests
Phase 5: Deploy to staging

Sub-agent A: audit
Sub-agent B: implementation
"""
    * 3
)  # make it HEAVY

budget_5 = assess_context_budget(
    large_task,
    current_session_chars=50_000,
)
_assert(
    budget_5.task_complexity == TaskComplexity.HEAVY,
    f"complexity HEAVY (got {budget_5.task_complexity.value})",
)

plan_5 = decide_execution_shape(
    task_text=large_task,
    context_budget=budget_5,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(
        can_parallelize=False,
        max_parallel_agents=1,
        resource_pressure_level="high",
    ),
)
_assert(
    plan_5.mode == OrchestrationMode.SEQUENTIAL_PHASES,
    f"mode is SEQUENTIAL (got {plan_5.mode.value})",
)
_assert(not plan_5.use_parallelism, "no parallelism under constrained compute")


# ── Test 6: Critical pressure → checkpoint/summarization required ──────────
print("\n6. Critical context pressure → checkpoint/summary required")

budget_6 = assess_context_budget(
    "Phase 1: Do X\nPhase 2: Do Y\nPhase 3: Do Z\n" * 5,
    current_session_chars=500_000,  # > 75% of 560K → CRITICAL
)
_assert(
    budget_6.pressure == ContextPressure.CRITICAL,
    f"pressure CRITICAL (got {budget_6.pressure.value})",
)
_assert(budget_6.should_checkpoint_before_run, "checkpoint before run")
_assert(budget_6.should_force_summary_between_phases, "force summary between phases")
_assert(budget_6.should_decompose, "should decompose")

_assert(
    should_checkpoint_now(ContextPressure.CRITICAL, TaskComplexity.MEDIUM),
    "checkpoint_now for CRITICAL + MEDIUM",
)
_assert(
    should_force_summary(ContextPressure.CRITICAL, TaskComplexity.SMALL, 1),
    "force_summary for CRITICAL (any complexity)",
)


# ── Test 7: Traceability record written correctly ──────────────────────────
print("\n7. Traceability record written correctly")

# Use a temp file to avoid polluting real logs
with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as tmp:
    tmp_path = tmp.name

try:
    store = OrchestrationRecordStore(path=tmp_path)
    record = OrchestrationRecord.from_plan(
        plan_4,
        task_id="test_task_001",
        correlation_id="corr_test_001",
        metadata={"test": True},
    )

    store.append(record)
    _assert(store.count() == 1, "record stored (count=1)")

    # Read it back
    records = store.recent(limit=5)
    _assert(len(records) == 1, "one record retrieved")
    r = records[0]
    _assert(r.task_id == "test_task_001", "task_id correct")
    _assert(r.mode == "planner_executor_verifier", f"mode correct (got {r.mode})")
    _assert(r.require_verifier, "require_verifier stored")
    _assert(r.require_planner, "require_planner stored")
    _assert(r.risk_level == "high", f"risk_level correct (got {r.risk_level})")
    _assert(
        "checkpoint_between_phases" in r.checkpoint_decisions,
        "checkpoint decisions stored",
    )

    # Mark completed
    store.mark_completed(record.record_id, execution_path="planner→executor→verifier")
    records = store.recent(limit=5)
    _assert(records[0].completed_at != "", "completed_at set")
    _assert(
        records[0].execution_path == "planner→executor→verifier", "execution_path set"
    )

    # Query helpers
    by_mode = store.by_mode("planner_executor_verifier")
    _assert(len(by_mode) == 1, "by_mode query works")

    with_v = store.with_verifier()
    _assert(len(with_v) == 1, "with_verifier query works")

    by_task = store.by_task_id("test_task_001")
    _assert(by_task is not None, "by_task_id query works")

finally:
    os.unlink(tmp_path)


# ── Test 8: Backward compatibility ─────────────────────────────────────────
print("\n8. Backward compatibility — simple tasks unchanged")

from umh.substrate.conversation_router import route_message

# Simple message should still route correctly
result_simple = route_message("hello")
_assert(
    result_simple["routed_to"] == "task_pipeline", "simple msg routes to task_pipeline"
)
_assert("orchestration_plan" in result_simple, "orchestration_plan field present")
_assert(result_simple["is_query"] is False, "is_query is False")
_assert(result_simple["text"] == "hello", "text preserved")

# Query should still route to query_brain (or task_pipeline if stores unavailable)
result_query = route_message("what did I do yesterday?")
_assert(
    result_query["routed_to"] in ("query_brain", "task_pipeline"),
    f"query routes correctly (got {result_query['routed_to']})",
)

# Simple task plan should be SINGLE_AGENT
if result_simple.get("orchestration_plan"):
    _assert(
        result_simple["orchestration_plan"]["mode"] == "single_agent",
        "simple task gets SINGLE_AGENT plan",
    )


# ── Test 9: Compute-aware preferences ──────────────────────────────────────
print("\n9. Compute-aware preferences reflected in plan")

# Browser intent → should prefer local when local is online
budget_browser = assess_context_budget("open YouTube and play music")
plan_browser = decide_execution_shape(
    task_text="open YouTube and play music",
    context_budget=budget_browser,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(local_online=True),
    task_metadata={"is_browser_intent": True},
)
_assert(
    plan_browser.preferred_node == PreferredNode.LOCAL,
    f"browser intent prefers LOCAL (got {plan_browser.preferred_node.value})",
)

# Heavy task → should prefer VPS
budget_heavy = assess_context_budget("Phase 1: X\nPhase 2: Y\nPhase 3: Z\n" * 10)
plan_heavy = decide_execution_shape(
    task_text="Phase 1: X\nPhase 2: Y\nPhase 3: Z\n" * 10,
    context_budget=budget_heavy,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(local_online=True),
)
_assert(
    plan_heavy.preferred_node == PreferredNode.VPS,
    f"heavy task prefers VPS (got {plan_heavy.preferred_node.value})",
)

# High resource pressure → reduced parallelism
plan_constrained = decide_execution_shape(
    task_text=parallel_task,
    context_budget=budget_3,
    risk_level=RiskLevel.LOW,
    available_compute=AvailableCompute(
        can_parallelize=True,
        max_parallel_agents=4,
        resource_pressure_level="high",
    ),
)
if plan_constrained.mode == OrchestrationMode.PARALLEL_SUBAGENTS:
    _assert(
        plan_constrained.max_subagents <= 2,
        f"high pressure reduces agents (got {plan_constrained.max_subagents})",
    )


# ── Test 10: Phase summarization helpers ────────────────────────────────────
print("\n10. Phase summarization and compression helpers")

long_output = "A" * 5000
summary = summarize_phase_output(long_output, max_chars=200)
_assert(len(summary) <= 200, f"summary within budget (got {len(summary)})")
_assert("[... compressed ...]" in summary, "compression marker present")

short_output = "Short result"
summary_short = summarize_phase_output(short_output, max_chars=200)
_assert(summary_short == short_output, "short output preserved as-is")

compressed = compress_for_next_phase(
    long_output,
    carry_forward=["key fact 1", "key fact 2"],
    max_chars=500,
)
_assert(len(compressed) <= 500, f"compressed within budget (got {len(compressed)})")
_assert("Carry forward:" in compressed, "carry-forward section present")
_assert("key fact 1" in compressed, "carry-forward items preserved")


# ── Test 11: Sub-agent budget allocation ────────────────────────────────────
print("\n11. Sub-agent budget allocation")

budgets = allocate_subagent_budgets(
    total_budget_chars=200_000,
    num_subagents=4,
)
_assert(len(budgets) == 4, f"4 budgets allocated (got {len(budgets)})")
_assert(all(b > 0 for b in budgets), "all budgets positive")
_assert(sum(budgets) <= 200_000, "total within limit")

# Too many agents for small budget → reduces agent count
budgets_small = allocate_subagent_budgets(
    total_budget_chars=30_000,
    num_subagents=10,
)
_assert(
    len(budgets_small) < 10,
    f"budget-constrained: fewer agents (got {len(budgets_small)})",
)
_assert(
    all(b >= 20_000 for b in budgets_small),
    "each agent gets minimum viable budget",
)


# ── Results ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {_PASS} passed, {_FAIL} failed")
print("=" * 60)

sys.exit(0 if _FAIL == 0 else 1)
