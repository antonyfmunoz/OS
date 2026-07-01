#!/usr/bin/env python3
"""M1 Operator MVP Closure — verification script.

Checks that G10 (Proof Inspector) and G11 (Recovery Dashboard) are wired
end-to-end: backend routes, frontend stores, panels, and registrations.
Also checks Phase 3 quality fixes.
"""

from __future__ import annotations

import os
import sys

REPO = os.environ.get("UMH_ROOT", "/opt/OS")
PASS = 0
FAIL = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def file_exists(rel: str) -> bool:
    return os.path.isfile(os.path.join(REPO, rel))


def file_contains(rel: str, needle: str) -> bool:
    path = os.path.join(REPO, rel)
    if not os.path.isfile(path):
        return False
    with open(path) as f:
        return needle in f.read()


def file_line_count(rel: str) -> int:
    path = os.path.join(REPO, rel)
    if not os.path.isfile(path):
        return -1
    with open(path) as f:
        return sum(1 for _ in f)


def main() -> int:
    print("M1 Operator MVP Closure — Verification")
    print(f"Repo: {REPO}")

    # ── G10: Proof Inspector ──
    section("G10: Proof Inspector Panel")

    check("Backend routes exist",
          file_exists("transports/api/cockpit_proof_inspector_routes.py"))
    check("Backend has governed_mutation for approve",
          file_contains("transports/api/cockpit_proof_inspector_routes.py",
                        'governed_mutation'))
    check("Zustand store exists",
          file_exists("cockpit/src/renderer/stores/proofInspectorStore.ts"))
    check("Panel component exists",
          file_exists("cockpit/src/renderer/panels/ProofInspectorPanel.tsx"))
    check("Panel registered in cockpitStore",
          file_contains("cockpit/src/renderer/stores/cockpitStore.ts",
                        "'proofinspector'"))
    check("Panel registered in routes.ts",
          file_contains("cockpit/src/renderer/types/routes.ts",
                        "'proofinspector'"))
    check("Panel registered in Shell.tsx",
          file_contains("cockpit/src/renderer/components/Shell.tsx",
                        "ProofInspectorPanel"))
    check("Routes mounted in cockpit.py",
          file_contains("transports/api/cockpit.py",
                        "_mount_proof_inspector_router"))

    # ── G11: Recovery Dashboard ──
    section("G11: Recovery Dashboard Panel")

    check("Backend routes exist",
          file_exists("transports/api/cockpit_recovery_dashboard_routes.py"))
    check("Backend has governed_mutation for execute",
          file_contains("transports/api/cockpit_recovery_dashboard_routes.py",
                        'governed_mutation'))
    check("Zustand store exists",
          file_exists("cockpit/src/renderer/stores/recoveryDashboardStore.ts"))
    check("Panel component exists",
          file_exists("cockpit/src/renderer/panels/RecoveryDashboardPanel.tsx"))
    check("Panel registered in cockpitStore",
          file_contains("cockpit/src/renderer/stores/cockpitStore.ts",
                        "'recoverydashboard'"))
    check("Panel registered in routes.ts",
          file_contains("cockpit/src/renderer/types/routes.ts",
                        "'recoverydashboard'"))
    check("Panel registered in Shell.tsx",
          file_contains("cockpit/src/renderer/components/Shell.tsx",
                        "RecoveryDashboardPanel"))
    check("Routes mounted in cockpit.py",
          file_contains("transports/api/cockpit.py",
                        "_mount_recovery_dashboard_router"))

    # ── Phase 3: Quality ──
    section("Phase 3: Quality Cleanup")

    check("MutationStore fixed in PLATFORM_SPEC",
          file_contains("PLATFORM_SPEC.md", "MutationRegistry"))
    check("No MutationStore in PLATFORM_SPEC",
          not file_contains("PLATFORM_SPEC.md", "MutationStore"))
    check("BenchmarkOutcomeRecord renamed",
          file_contains("substrate/organism/benchmarks/outcome_accuracy.py",
                        "BenchmarkOutcomeRecord"))
    check("No duplicate OutcomeRecord in benchmarks",
          not file_contains("substrate/organism/benchmarks/outcome_accuracy.py",
                            "class OutcomeRecord:"))
    check("ApprovalStore deprecated notice",
          file_contains("substrate/state/stores/approval_store.py",
                        "DEPRECATED"))
    check("Dead TrackingPanel removed",
          not file_exists("cockpit/src/renderer/panels/TrackingPanel.tsx"))
    check("Dead ExperimentsPanel removed",
          not file_exists("cockpit/src/renderer/panels/ExperimentsPanel.tsx"))
    check("No tracking in cockpitStore",
          not file_contains("cockpit/src/renderer/stores/cockpitStore.ts",
                            "'tracking'"))
    check("No experiments in cockpitStore",
          not file_contains("cockpit/src/renderer/stores/cockpitStore.ts",
                            "'experiments'"))

    # ── File size limits ──
    section("File Size Limits")

    main_routes = file_line_count("transports/api/cockpit_operator_loop_routes.py")
    check(f"Main operator routes under 3000 lines ({main_routes})",
          0 < main_routes < 3000,
          "SKIP if route split not yet merged" if main_routes >= 3000 else "")

    cockpit_py = file_line_count("transports/api/cockpit.py")
    check(f"cockpit.py under 3000 lines ({cockpit_py})",
          0 < cockpit_py < 3000)

    # ── Pre-commit gates ──
    section("Pre-commit Gates")

    # Handle worktree .git (may be a file pointing to the real git dir)
    git_dir = os.path.join(REPO, ".git")
    if os.path.isfile(git_dir):
        with open(git_dir) as f:
            line = f.read().strip()
        if line.startswith("gitdir:"):
            real_git = line.split(":", 1)[1].strip()
            if not os.path.isabs(real_git):
                real_git = os.path.join(REPO, real_git)
            real_git = os.path.normpath(real_git)
            # worktrees store a commondir file pointing to the shared .git
            commondir_file = os.path.join(real_git, "commondir")
            if os.path.isfile(commondir_file):
                with open(commondir_file) as cf:
                    common_rel = cf.read().strip()
                common_dir = os.path.normpath(os.path.join(real_git, common_rel))
            else:
                common_dir = real_git
            hook_path = os.path.join(common_dir, "hooks", "pre-commit")
        else:
            hook_path = os.path.join(git_dir, "hooks", "pre-commit")
    else:
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
    if os.path.isfile(hook_path):
        with open(hook_path) as f:
            hook = f.read()
        check("Credential injection gate wired",
              "check_credential_injection" in hook)
        check("Secret patterns gate wired",
              "check_secret_patterns" in hook)
        check("Mesh relay firewall gate wired",
              "check_mesh_relay_firewall" in hook)
    else:
        check("Pre-commit hook exists", False, hook_path)

    # ── Summary ──
    section("SUMMARY")
    total = PASS + FAIL
    print(f"\n  {PASS}/{total} checks passed")
    if FAIL > 0:
        print(f"  {FAIL} FAILURES — review above")
        return 1
    else:
        print("  ALL CHECKS PASSED — G10 + G11 + Phase 3 verified")
        return 0


if __name__ == "__main__":
    sys.exit(main())
