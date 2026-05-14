"""Operationalization engine end-to-end validation.

Exercises the full canonical runtime spine:
  signal → interpretation → capability resolution → adapter selection
  → environment selection → governance evaluation → execution
  → observability → replay determinism

Phase 96.8BO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

from execution.runtime.execution_contracts_v1 import SignalSource
from execution.runtime.environment_registry_v1 import EnvironmentRegistry
from execution.runtime.capability_router_v1 import CapabilityRouter
from adapters.adapter_engine.adapter_lifecycle_manager_v1 import AdapterLifecycleManager
from execution.runtime.governance_execution_bridge_v1 import GovernanceExecutionBridge
from execution.runtime.runtime_execution_queue_v1 import RuntimeExecutionQueue
from execution.runtime.runtime_observability_pipeline_v1 import RuntimeObservabilityPipeline
from execution.runtime.execution_orchestrator_v1 import ExecutionOrchestrator
from execution.runtime.canonical_runtime_spine_v1 import CanonicalRuntimeSpine
from execution.runtime.runtime_replay_engine_v1 import RuntimeReplayEngine

PROOF_DIR = Path("data/runtime/operationalization_proofs")


def setup_spine() -> CanonicalRuntimeSpine:
    env_registry = EnvironmentRegistry.create_default()
    router = CapabilityRouter(env_registry)

    adapter_mgr = AdapterLifecycleManager()
    adapter_mgr.register_adapter(
        "vps-shell-01", "shell_adapter",
        ["ping", "explore-environment", "relay-status", "tmux-status",
         "git-status", "git-log"], "vps_tmux",
    )
    adapter_mgr.register_adapter(
        "vps-report-01", "report_adapter",
        ["constitution-report", "economics-report", "continuity-report",
         "orchestration-report", "runtime-status", "capabilities",
         "adapters", "execution-queue", "resume-runtime", "runtime-replay",
         "capability-report", "adapter-report", "federation-report",
         "governance-intelligence-report", "strategy-report", "epistemic-report",
         "identity-report", "telos-report", "resilience-report"],
        "vps_tmux",
    )
    adapter_mgr.register_adapter(
        "vps-memory-01", "memory_adapter",
        ["memory-query", "memory-lineage", "promote-safe-memory-candidate"],
        "vps_tmux",
    )
    adapter_mgr.register_adapter(
        "vps-ingest-01", "ingestion_adapter",
        ["ingest-safe-doc-cu", "ingest-safe-doc"], "vps_tmux",
    )

    governance = GovernanceExecutionBridge(
        decisions_dir="data/runtime/operationalization_governance",
    )
    queue = RuntimeExecutionQueue(queue_dir="data/runtime/operationalization_queue")
    observability = RuntimeObservabilityPipeline(
        observability_dir="data/runtime/operationalization_observability",
    )
    orchestrator = ExecutionOrchestrator(adapter_mgr, observability)

    spine = CanonicalRuntimeSpine(
        capability_router=router,
        adapter_manager=adapter_mgr,
        environment_registry=env_registry,
        governance_bridge=governance,
        execution_queue=queue,
        orchestrator=orchestrator,
        observability=observability,
    )
    spine.start_session("validation-session-001")
    return spine


SAFE_COMMANDS = [
    "!ping",
    "!runtime-status",
    "!capabilities",
    "!adapters",
    "!execution-queue",
    "!resume-runtime",
    "!git-status",
    "!git-log",
    "!memory-query",
    "!memory-lineage",
    "!constitution-report",
    "!economics-report",
    "!continuity-report",
    "!orchestration-report",
    "!explore-environment",
    "!relay-status",
]

GOVERNED_COMMANDS = [
    "!ingest-safe-doc-cu",
    "!ingest-safe-doc",
]

FORBIDDEN_COMMANDS = [
    "!self-govern",
    "!wallet-execution",
]

UNKNOWN_COMMANDS = [
    "!nonexistent-xyz-command",
]


def run() -> dict:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    spine = setup_spine()
    proof: dict = {"validation_type": "operationalization_validation", "tests": []}

    # Test 1: Safe commands all succeed
    print("Test 1: Safe commands...")
    safe_results = []
    for cmd in SAFE_COMMANDS:
        result = spine.execute(cmd)
        safe_results.append(result)
    all_safe = all(r.succeeded for r in safe_results)
    test = {
        "test": "safe_commands",
        "total": len(SAFE_COMMANDS),
        "succeeded": sum(1 for r in safe_results if r.succeeded),
        "pass": all_safe,
    }
    proof["tests"].append(test)
    print(f"  {test['succeeded']}/{test['total']} safe commands succeeded — {'PASS' if all_safe else 'FAIL'}")
    for r in safe_results:
        if not r.succeeded:
            print(f"    FAILED: {r.command_name} → {r.outcome.value}: {r.error_message}")

    # Test 2: Governed commands succeed
    print("Test 2: Governed commands...")
    gov_results = []
    for cmd in GOVERNED_COMMANDS:
        result = spine.execute(cmd)
        gov_results.append(result)
    all_gov = all(r.succeeded for r in gov_results)
    test = {
        "test": "governed_commands",
        "total": len(GOVERNED_COMMANDS),
        "succeeded": sum(1 for r in gov_results if r.succeeded),
        "pass": all_gov,
    }
    proof["tests"].append(test)
    print(f"  {test['succeeded']}/{test['total']} governed commands succeeded — {'PASS' if all_gov else 'FAIL'}")

    # Test 3: Forbidden commands denied
    print("Test 3: Forbidden commands...")
    forbidden_results = []
    for cmd in FORBIDDEN_COMMANDS:
        result = spine.execute(cmd)
        forbidden_results.append(result)
    all_forbidden = all(not r.succeeded for r in forbidden_results)
    test = {
        "test": "forbidden_commands",
        "total": len(FORBIDDEN_COMMANDS),
        "denied": sum(1 for r in forbidden_results if not r.succeeded),
        "pass": all_forbidden,
    }
    proof["tests"].append(test)
    print(f"  {test['denied']}/{test['total']} forbidden commands denied — {'PASS' if all_forbidden else 'FAIL'}")

    # Test 4: Unknown commands fail with capability unavailable
    print("Test 4: Unknown commands...")
    unknown_results = []
    for cmd in UNKNOWN_COMMANDS:
        result = spine.execute(cmd)
        unknown_results.append(result)
    all_unknown = all(not r.succeeded for r in unknown_results)
    test = {
        "test": "unknown_commands",
        "total": len(UNKNOWN_COMMANDS),
        "rejected": sum(1 for r in unknown_results if not r.succeeded),
        "pass": all_unknown,
    }
    proof["tests"].append(test)
    print(f"  {test['rejected']}/{test['total']} unknown commands rejected — {'PASS' if all_unknown else 'FAIL'}")

    # Test 5: Stats consistency
    print("Test 5: Stats consistency...")
    stats = spine.get_stats()
    # Only commands that reach the orchestrator are counted (forbidden/unknown exit early)
    expected_count = len(SAFE_COMMANDS) + len(GOVERNED_COMMANDS)
    test = {
        "test": "stats_consistency",
        "expected_executions": expected_count,
        "actual_executions": stats["executions_count"],
        "pass": stats["executions_count"] == expected_count,
    }
    proof["tests"].append(test)
    print(f"  Expected {expected_count}, got {stats['executions_count']} — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 6: Observability records
    print("Test 6: Observability records...")
    obs_stats = stats.get("observability", {})
    test = {
        "test": "observability_records",
        "total_recorded": obs_stats.get("total_recorded", 0),
        "pass": obs_stats.get("total_recorded", 0) > 0,
    }
    proof["tests"].append(test)
    print(f"  {obs_stats.get('total_recorded', 0)} observability records — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 7: Governance decisions persisted
    print("Test 7: Governance decisions...")
    gov_stats = stats.get("governance", {})
    test = {
        "test": "governance_decisions",
        "total_decisions": gov_stats.get("total_decisions", 0),
        "pass": gov_stats.get("total_decisions", 0) > 0,
    }
    proof["tests"].append(test)
    print(f"  {gov_stats.get('total_decisions', 0)} governance decisions — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 8: Replay determinism
    print("Test 8: Replay determinism...")
    env_registry = EnvironmentRegistry.create_default()
    router = CapabilityRouter(env_registry)
    replay_gov = GovernanceExecutionBridge(
        decisions_dir="data/runtime/operationalization_replay_governance",
    )
    replay_engine = RuntimeReplayEngine(router, replay_gov, proof_dir=str(PROOF_DIR))

    replay_records = [
        {"record_id": f"obs-{i}", "command_name": cmd.lstrip("!"),
         "risk_class": "safe", "governance_verdict": "approved"}
        for i, cmd in enumerate(SAFE_COMMANDS[:5])
    ]
    session_result = replay_engine.replay_session(replay_records, session_id="validation-replay")
    test = {
        "test": "replay_determinism",
        "total_records": session_result.total_records,
        "passed_records": session_result.passed_records,
        "total_checks": session_result.total_checks,
        "passed_checks": session_result.passed_checks,
        "all_passed": session_result.all_passed,
        "pass": session_result.all_passed,
    }
    proof["tests"].append(test)
    print(f"  {session_result.passed_checks}/{session_result.total_checks} replay checks — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 9: Environment registry
    print("Test 9: Environment registry...")
    env_stats = stats.get("environments", {})
    test = {
        "test": "environment_registry",
        "total_environments": env_stats.get("total", 0),
        "available": env_stats.get("available", 0),
        "pass": env_stats.get("total", 0) == 3,
    }
    proof["tests"].append(test)
    print(f"  {env_stats.get('total', 0)} environments ({env_stats.get('available', 0)} available) — {'PASS' if test['pass'] else 'FAIL'}")

    # Test 10: Adapter stats
    print("Test 10: Adapter stats...")
    adapter_stats = stats.get("adapters", {})
    test = {
        "test": "adapter_stats",
        "total_adapters": adapter_stats.get("total", 0),
        "available": adapter_stats.get("available", 0),
        "pass": adapter_stats.get("total", 0) >= 4,
    }
    proof["tests"].append(test)
    print(f"  {adapter_stats.get('total', 0)} adapters ({adapter_stats.get('available', 0)} available) — {'PASS' if test['pass'] else 'FAIL'}")

    # Summary
    all_pass = all(t["pass"] for t in proof["tests"])
    proof["all_pass"] = all_pass
    proof["total_tests"] = len(proof["tests"])
    proof["passed"] = sum(1 for t in proof["tests"] if t["pass"])

    proof_path = PROOF_DIR / "operationalization_validation_proof.json"
    with open(proof_path, "w") as f:
        json.dump(proof, f, indent=2)

    print(f"\nRESULT: {proof['passed']}/{proof['total_tests']} PASS")
    print(f"Proof saved: {proof_path}")

    return proof


if __name__ == "__main__":
    run()
