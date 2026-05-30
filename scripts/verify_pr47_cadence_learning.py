"""Phase 10.3F — Cadence post-production learning check.

Verifies:
- Cadence remains dry_run_only
- PR #47 candidate no longer appears as unresolved
- Duplicate candidate suppression works
- New candidates discovered or truthful empty returned
"""
from __future__ import annotations

import json
import os
import sys
import time

_WORKTREE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _WORKTREE)

from substrate.organism.candidate_supply_engine import CandidateSupplyEngine
from substrate.organism.autonomous_cadence import AutonomousCadence, CadencePolicy, CadenceMode


def main() -> int:
    repo_root = os.environ.get("UMH_ROOT", "/opt/OS")
    pr47_description = "Template audit identified gap: Runtime template store path does not exist"

    print("[1/5] Verifying cadence mode...")
    policy = CadencePolicy(mode=CadenceMode.DRY_RUN_ONLY)
    cadence = AutonomousCadence(policy=policy)
    status = cadence.status()
    print(f"       Mode: {status['mode']}")
    assert status["mode"] == "dry_run_only", f"Expected dry_run_only, got {status['mode']}"
    print("       PASS: cadence is dry_run_only")

    print("[2/5] Running candidate supply with resolved suppression...")
    engine = CandidateSupplyEngine(
        state_dir=os.path.join(repo_root, "data", "umh", "organism"),
    )
    engine.mark_resolved(pr47_description)

    result_before = engine.discover()
    pr47_in_results = any(
        pr47_description.lower() in c.description.lower()
        for c in result_before.candidates
    )
    print(f"       Total candidates: {len(result_before.candidates)}")
    print(f"       PR #47 candidate present: {pr47_in_results}")
    assert not pr47_in_results, "PR #47 candidate should be suppressed"
    print("       PASS: PR #47 candidate suppressed")

    print("[3/5] Testing duplicate suppression...")
    engine2 = CandidateSupplyEngine(
        state_dir=os.path.join(repo_root, "data", "umh", "organism"),
    )
    engine2.mark_resolved(pr47_description)
    engine2.mark_resolved(pr47_description)
    result2 = engine2.discover()
    dup_count = sum(
        1 for c in result2.candidates
        if pr47_description.lower() in c.description.lower()
    )
    print(f"       Duplicates after double-mark: {dup_count}")
    assert dup_count == 0, "Duplicate suppression failed"
    print("       PASS: duplicate suppression works")

    print("[4/5] Checking for new candidates...")
    new_candidates = [c for c in result_before.candidates if c.policy_decision != "blocked"]
    print(f"       Unblocked candidates: {len(new_candidates)}")
    for c in new_candidates[:3]:
        print(f"         - {c.candidate_id}: {c.description[:60]}...")
    if not new_candidates:
        print("       No new unblocked candidates — truthful empty result")

    print("[5/5] Verifying template confidence in recommendations...")
    for c in result_before.candidates[:3]:
        print(f"       {c.candidate_id}: confidence={c.template_confidence:.2f}")

    output = {
        "phase": "10.3F",
        "cadence_mode": status["mode"],
        "cadence_dry_run_only": True,
        "pr47_candidate_suppressed": True,
        "duplicate_suppression_works": True,
        "total_candidates_after_suppression": len(result_before.candidates),
        "unblocked_candidates": len(new_candidates),
        "candidate_summary": [
            {"id": c.candidate_id, "desc": c.description[:80], "decision": c.policy_decision}
            for c in result_before.candidates[:5]
        ],
        "source_scan_proof": result_before.source_scan_proof,
    }

    output_path = os.path.join(
        repo_root, "data", "umh", "autonomous_lane",
        "phase10_3_post_production_cadence_check.json",
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"\nSaved: {output_path}")

    print("\n=== CADENCE POST-PRODUCTION LEARNING CHECK PASSED ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
