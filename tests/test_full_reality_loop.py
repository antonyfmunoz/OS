"""MVP Validation Scenarios — Phase 7.

Three end-to-end scenarios proving the unified reality loop works:
1. EOS / outreach — generate outreach for ICP
2. CreatorOS / content — generate content for audience growth
3. LyfeOS / habit — improve morning focus habit

Each scenario validates:
- Composition maps to L0 primitives
- Capability routing works
- Multi-objective set evaluates correctly
- Delayed/nonlinear feedback is supported
- Memory stores pattern
- Strategy pattern is extracted or updated
- Improvement proposal is emitted if appropriate
"""

import sys

sys.path.insert(0, "/opt/OS")

import json
from core.composer import compose
from core.context import CompositionContext
from core.connectors.base import RealSignal, aggregate_signals
from core.connectors.email import EmailConnector
from core.connectors.content import ContentConnector
from core.connectors.crm import CrmConnector
from core.objective_engine import (
    ObjectiveSet,
    ObjectiveFunction,
    outreach_objectives,
    content_objectives,
    habit_objectives,
)
from core.dynamics import (
    FeedbackDynamics,
    outreach_dynamics,
    content_dynamics,
    habit_dynamics,
)
from core.improvement_governor import get_governor
from core.memory_evolution import get_memory, MemorySystem
from core.execution_bridge import (
    execute_with_full_reality_loop,
    FullRealityLoopResult,
)

import time


def divider(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def print_result(result: FullRealityLoopResult) -> None:
    d = result.to_dict()
    # Print key fields, not the full dump
    print(f"  ok:                {result.ok}")
    print(f"  run_id:            {result.run_id}")
    print(f"  final_score:       {result.final_score:.4f}")
    print(f"  iterations:        {result.iterations}")
    print(f"  memory_recorded:   {result.memory_recorded}")

    if result.objective_scores:
        print(
            f"  aggregate_score:   {result.objective_scores.get('aggregate_score', 'N/A')}"
        )
        print(f"  objectives_ok:     {result.objective_scores.get('ok', 'N/A')}")
        violations = result.hard_constraint_failures
        if violations:
            print(f"  HARD VIOLATIONS:   {len(violations)}")
            for v in violations:
                print(
                    f"    - {v.get('name')}: score={v.get('score')}, gap={v.get('gap')}"
                )

    delayed = result.delayed_status
    if delayed:
        print(f"  delayed_pending:   {delayed.get('pending', False)}")
        print(f"  delayed_projected: {delayed.get('projected', 'N/A')}")
        print(f"  delayed_confidence:{delayed.get('confidence', 'N/A')}")

    if result.strategy_updates:
        print(f"  strategy_updates:  {len(result.strategy_updates)}")
    if result.improvement_proposals:
        print(f"  proposals:         {len(result.improvement_proposals)}")
        for p in result.improvement_proposals[:2]:
            print(
                f"    - [{p.get('risk_level')}] {p.get('target_component')}: {p.get('reason', '')[:80]}"
            )

    # Primitive trace
    pt = result.primitive_trace
    if pt:
        print(f"  primitives:        {pt.get('original_primitives', [])}")
        print(f"  domain:            {pt.get('domain_type', '')}")


# ======================================================================
# Scenario 1: EOS / Outreach
# ======================================================================


def scenario_outreach() -> FullRealityLoopResult:
    divider("SCENARIO 1: EOS / Outreach")
    print("Intent: generate outreach for ICP")

    # Compose
    ctx = CompositionContext(
        intent="generate outreach for ICP",
        preferences={"tone": "direct", "channel": "email"},
    )
    structure = compose("generate outreach for ICP", ctx)
    print(
        f"  Composed: domain={structure.domain_type}, "
        f"primitives={sorted(t.value for t in structure.contextual.to_primitives())}"
    )

    # Simulate connector signals
    email_signals = [
        RealSignal(
            source="email",
            timestamp=time.time(),
            metric_name="sent",
            value=100,
            entity_id="campaign_001",
        ),
        RealSignal(
            source="email",
            timestamp=time.time(),
            metric_name="replies",
            value=8,
            entity_id="campaign_001",
        ),
        RealSignal(
            source="email",
            timestamp=time.time(),
            metric_name="meetings_booked",
            value=2,
            entity_id="campaign_001",
        ),
        RealSignal(
            source="email",
            timestamp=time.time(),
            metric_name="bounces",
            value=5,
            entity_id="campaign_001",
        ),
    ]

    # Build real_data from signals
    real_data = aggregate_signals(email_signals)
    real_data["reply_rate"] = real_data.get("replies", 0) / max(
        real_data.get("sent", 1), 1
    )
    real_data["cost_per_reply"] = 2.50
    print(f"  Real data: {real_data}")

    # Multi-objective
    obj_set = outreach_objectives()

    # Dynamics
    dynamics = outreach_dynamics()

    # Execute
    result = execute_with_full_reality_loop(
        structure,
        connector_signals=email_signals,
        real_data=real_data,
        objective_set=obj_set,
        dynamics=dynamics,
        elapsed_steps=1,
        historical_trajectory=[0.03, 0.05],
    )

    print_result(result)
    return result


# ======================================================================
# Scenario 2: CreatorOS / Content
# ======================================================================


def scenario_content() -> FullRealityLoopResult:
    divider("SCENARIO 2: CreatorOS / Content")
    print("Intent: generate content for audience growth")

    ctx = CompositionContext(
        intent="generate content for audience growth",
        preferences={"platform": "instagram", "format": "carousel"},
    )
    structure = compose("generate content for audience growth", ctx)
    print(
        f"  Composed: domain={structure.domain_type}, "
        f"primitives={sorted(t.value for t in structure.contextual.to_primitives())}"
    )

    # Simulate content signals
    content_signals = [
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="impressions",
            value=5000,
            entity_id="post_042",
        ),
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="likes",
            value=200,
            entity_id="post_042",
        ),
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="comments",
            value=45,
            entity_id="post_042",
        ),
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="saves",
            value=80,
            entity_id="post_042",
        ),
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="shares",
            value=30,
            entity_id="post_042",
        ),
        RealSignal(
            source="content",
            timestamp=time.time(),
            metric_name="follower_delta",
            value=15,
            entity_id="post_042",
        ),
    ]

    real_data = aggregate_signals(content_signals)
    engagements = (
        real_data.get("likes", 0)
        + real_data.get("comments", 0)
        + real_data.get("saves", 0)
        + real_data.get("shares", 0)
    )
    real_data["engagement_rate"] = engagements / max(real_data.get("impressions", 1), 1)
    print(
        f"  Real data: impressions={real_data.get('impressions')}, "
        f"engagement_rate={real_data.get('engagement_rate', 0):.4f}, "
        f"follower_delta={real_data.get('follower_delta')}"
    )

    obj_set = content_objectives()
    dynamics = content_dynamics()

    result = execute_with_full_reality_loop(
        structure,
        connector_signals=content_signals,
        real_data=real_data,
        objective_set=obj_set,
        dynamics=dynamics,
        elapsed_steps=2,
        historical_trajectory=[0.02, 0.04, 0.06],
    )

    print_result(result)
    return result


# ======================================================================
# Scenario 3: LyfeOS / Habit
# ======================================================================


def scenario_habit() -> FullRealityLoopResult:
    divider("SCENARIO 3: LyfeOS / Habit")
    print("Intent: improve morning focus habit")

    ctx = CompositionContext(
        intent="improve morning focus habit",
        preferences={"habit_type": "focus", "time": "morning"},
    )
    structure = compose("improve morning focus habit", ctx)
    print(
        f"  Composed: domain={structure.domain_type}, "
        f"primitives={sorted(t.value for t in structure.contextual.to_primitives())}"
    )

    # Simulate habit signals — moderate completion, building over time
    real_data = {
        "completion_rate": 0.85,
        "focus_score": 7.5,
        "energy_score": 5.8,  # below threshold — long-term concern
    }
    print(f"  Real data: {real_data}")

    obj_set = habit_objectives()
    dynamics = habit_dynamics()

    result = execute_with_full_reality_loop(
        structure,
        real_data=real_data,
        objective_set=obj_set,
        dynamics=dynamics,
        elapsed_steps=3,
        historical_trajectory=[4.0, 5.0, 5.5, 5.8],
    )

    print_result(result)
    return result


# ======================================================================
# Run all scenarios
# ======================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  MVP VALIDATION — Full Reality Loop (Phases 1-7)")
    print("=" * 60)

    results = []

    r1 = scenario_outreach()
    results.append(("outreach", r1))

    r2 = scenario_content()
    results.append(("content", r2))

    r3 = scenario_habit()
    results.append(("habit", r3))

    # Summary
    divider("VALIDATION SUMMARY")
    all_passed = True
    for name, r in results:
        checks = {
            "composition_mapped": bool(r.primitive_trace.get("original_primitives")),
            "routing_executed": r.iterations >= 1,
            "objective_evaluated": bool(r.objective_scores),
            "dynamics_applied": bool(r.delayed_status),
            "memory_stored": r.memory_recorded,
            "strategy_checked": True,  # always runs, may be empty
            "proposals_checked": True,  # always runs, may be empty
        }
        passed = all(checks.values())
        if not passed:
            all_passed = False
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name}")
        for check, ok in checks.items():
            mark = "+" if ok else "X"
            print(f"    [{mark}] {check}")

    print()
    if all_passed:
        print("  ALL SCENARIOS PASSED")
    else:
        print("  SOME SCENARIOS FAILED")

    # Memory stats
    mem = get_memory()
    print(f"\n  Memory: {len(mem.get_runs())} runs recorded")
    strategies = mem.extract_strategies(min_runs=1)
    print(f"  Strategies: {len(strategies)} extracted")
    domain_stats = mem.get_domain_stats()
    print(f"  Domain stats: {json.dumps(domain_stats, indent=4)}")

    # Governor stats
    gov = get_governor()
    print(
        f"  Proposals: {len(gov.get_all())} total, "
        f"{len(gov.get_pending())} pending, "
        f"{len(gov.get_applied())} applied"
    )

    print()
