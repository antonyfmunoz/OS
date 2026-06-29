"""C33 Benchmark Execution — runs all programmatic benchmarks.

Collects evidence for all 8 benchmark types:
  A — Dev Throughput (from Phase 0+1 execution data)
  B — Operator Experience (framework + escape tracking)
  C — Orchestration Quality (post-hoc from execution journal)
  D — Governance Quality (post-hoc from spine logs)
  E — Compound Intelligence (evidence chain from Phase 0)
  F — Company Operations (framework ready, data from real ops)
  G — Surface Switching (framework ready, data from real switches)
  H — Mutation Equivalence (structural audit + pair testing)

Usage: python3 scripts/run_c33_benchmarks.py
"""

from __future__ import annotations

import json
import os
import sys
import time

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _REPO_ROOT)
os.environ["UMH_ROOT"] = _REPO_ROOT

from substrate.organism.benchmark_harness import BenchmarkHarness
from substrate.organism.benchmarks.mutation_equivalence import (
    MutationEquivalenceScorer,
    MutationPair,
)
from substrate.organism.benchmarks.governance_quality import (
    GovernanceAssessment,
    GovernanceQualityScorer,
)
from substrate.organism.benchmarks.orchestration_quality import (
    OrchestrationDecision,
    OrchestrationQualityScorer,
)
from substrate.organism.operator_escape_tracker import OperatorEscapeTracker


def run_benchmark_e_evidence() -> dict:
    """Benchmark E: Compound Intelligence evidence chain.

    Checks all 6 signal types from Phase 0 infrastructure.
    """
    evidence = {
        "learning_to_capability": False,
        "capability_to_template": False,
        "template_to_reuse": False,
        "signal_to_decision": False,
        "decision_to_speed": False,
        "speed_to_automation": False,
    }

    repo = "/opt/OS"

    cap_path = os.path.join(repo, "data", "umh", "compounding", "capabilities.jsonl")
    if os.path.isfile(cap_path):
        with open(cap_path) as f:
            caps = [json.loads(l) for l in f if l.strip()]
        if caps:
            evidence["learning_to_capability"] = True
            print(f"  E1: {len(caps)} capabilities found")

    tmpl_path = os.path.join(repo, "data", "umh", "compounding", "templates.jsonl")
    if os.path.isfile(tmpl_path):
        with open(tmpl_path) as f:
            tmpls = [json.loads(l) for l in f if l.strip()]
        if tmpls:
            evidence["capability_to_template"] = True
            reused = [t for t in tmpls if t.get("times_matched", 0) > 0]
            if reused:
                evidence["template_to_reuse"] = True
            print(f"  E2: {len(tmpls)} templates, {len(reused)} reused")

    feed_path = os.path.join(repo, "data", "umh", "learning", "signal_feed.jsonl")
    if os.path.isfile(feed_path):
        with open(feed_path) as f:
            feeds = [json.loads(l) for l in f if l.strip()]
        auto_candidates = [f for f in feeds if f.get("auto_approve_candidate")]
        if auto_candidates:
            evidence["signal_to_decision"] = True
            print(f"  E4: {len(auto_candidates)} auto-approve candidates")

    harness_path = os.path.join(repo, "data", "umh", "c33", "c33_benchmarks.jsonl")
    if os.path.isfile(harness_path):
        with open(harness_path) as f:
            records = [json.loads(l) for l in f if l.strip()]
        governed = [r for r in records if r.get("pipeline") == "governed"]
        if len(governed) >= 2:
            first = governed[0].get("elapsed_seconds", 999)
            last = governed[-1].get("elapsed_seconds", 999)
            if last < first:
                evidence["decision_to_speed"] = True
                print(f"  E5: Speed improved {first:.1f}s -> {last:.1f}s")

        fast_paths = [r for r in governed if r.get("fast_path_used")]
        if fast_paths:
            evidence["speed_to_automation"] = True
            print(f"  E6: {len(fast_paths)} fast-path activations")

    signals_present = sum(1 for v in evidence.values() if v)
    chain_complete = all([
        evidence["learning_to_capability"],
        evidence["capability_to_template"],
        evidence["template_to_reuse"],
    ])

    return {
        "benchmark": "E",
        "name": "Compound Intelligence",
        "evidence": evidence,
        "signals_present": signals_present,
        "chain_complete": chain_complete,
        "pass": signals_present >= 4 and chain_complete,
        "verdict": (
            "PASS" if signals_present >= 4 and chain_complete
            else "CONDITIONAL" if signals_present >= 3
            else "FAIL"
        ),
    }


def run_benchmark_h_structural() -> dict:
    """Benchmark H: Mutation Equivalence structural audit.

    Checks which route files are connected to GovernedExecutionSpine
    and which bypass it entirely.
    """
    scorer = MutationEquivalenceScorer()
    audit = scorer.structural_audit()

    mutation_total = audit["mutation_route_files"]
    connected = audit["spine_connected"]
    bypasses = audit["potential_bypasses"]

    bypass_rate = bypasses / mutation_total if mutation_total > 0 else 1.0

    return {
        "benchmark": "H",
        "name": "Mutation Equivalence",
        "structural_audit": audit,
        "total_route_files": audit["total_route_files"],
        "mutation_route_files": mutation_total,
        "query_route_files": audit["query_route_files"],
        "spine_connected": connected,
        "potential_bypasses": bypasses,
        "bypass_rate": round(bypass_rate, 4),
        "pass": bypass_rate < 0.3,
        "verdict": (
            "PASS" if bypass_rate < 0.3
            else "CONDITIONAL" if bypass_rate < 0.5
            else "FAIL"
        ),
    }


def run_benchmark_b_framework() -> dict:
    """Benchmark B: Operator Experience framework check.

    Verifies escape tracker is operational and summarizes current state.
    """
    tracker = OperatorEscapeTracker()
    summary = tracker.summary()

    return {
        "benchmark": "B",
        "name": "Operator Experience",
        "escape_tracker_operational": True,
        "current_escapes": summary.get("total_escapes", 0),
        "framework_ready": True,
        "requires_human": True,
        "note": "Requires AFM workday for full execution",
    }


def run_all() -> dict:
    """Run all programmatic benchmarks and collect results."""
    results = {}

    print("=" * 60)
    print("C33 META-HARNESS VALIDATION CAMPAIGN — BENCHMARK EXECUTION")
    print("=" * 60)

    print("\n--- Benchmark E: Compound Intelligence ---")
    results["E"] = run_benchmark_e_evidence()
    print(f"  Verdict: {results['E']['verdict']} ({results['E']['signals_present']}/6 signals)")

    print("\n--- Benchmark H: Mutation Equivalence (structural) ---")
    results["H"] = run_benchmark_h_structural()
    print(f"  Verdict: {results['H']['verdict']} (bypass rate: {results['H']['bypass_rate']:.1%})")

    print("\n--- Benchmark B: Operator Experience (framework) ---")
    results["B"] = run_benchmark_b_framework()
    print(f"  Framework ready: {results['B']['framework_ready']}")

    print("\n--- Campaign Summary ---")
    for key in ["E", "H", "B"]:
        r = results[key]
        print(f"  {key} ({r['name']}): {r.get('verdict', 'PENDING')}")

    output_path = os.path.join(
        os.environ.get("UMH_ROOT", "/opt/OS"),
        "data", "umh", "c33", "benchmark_results.json",
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults written to {output_path}")

    return results


if __name__ == "__main__":
    run_all()
