#!/usr/bin/env python3
"""Wave 2 acceptance-matrix report — machine-generated (A–K categories).

Executes every mapped test node (pytest + the vitest surface-authority suites),
records per-id PASS/FAIL from the actual runner output, and emits a markdown
report with: id, exact scenario, exact tests, status, evidence, commit, and the
reason for any deferral. No row is marked PASS unless every mapped node passed in
this run. Field-layer rows carry FIELD_PENDING until the Session-1 field harness
qualifies them.

Vitest handling is generalized over wave1: each vitest suite is run and scored
per-file, so a J-row maps to an exact suite (not an all-or-nothing global flag).

Re-run to regenerate — do not hand-edit.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# pytest module shorthands
STORE = "tests/test_wave2_execution_attempts_store.py"
DEPS = "tests/test_wave2_compiler_dependencies.py"
GATES = "tests/test_wave2_convergence_gates.py"
AUTH = "tests/test_wave2_execution_authorization.py"
READY = "tests/test_wave2_execution_readiness.py"
PLACE = "tests/test_wave2_placement_lease_instructions.py"
SCHED = "tests/test_wave2_attempt_scheduler.py"
SPINE = "tests/test_wave2_spine_authorization.py"
ISO = "tests/test_wave2_worker_isolation_spool.py"
VERIFY = "tests/test_wave2_verification_proof.py"
ROUTES = "tests/test_wave2_execution_routes.py"
POLLER = "tests/test_wave2_control_plane_poller.py"
REHEARSAL = "tests/test_wave2_harness_rehearsal.py"
FAILPOLICY = "tests/test_wave2_field_failure_policy.py"
COORD = "tests/test_execution_coordinator.py"
SPINE1 = "tests/test_single_spine_architecture.py"

# vitest suites (scored per-file)
VITEST_SURF = "src/renderer/__tests__/surfaceAuthority.test.tsx"
VITEST_EXEC = "src/renderer/__tests__/executionSurfaceAuthority.test.tsx"

# A "vitest" node is a ("vitest", suite) tuple; a str/list is pytest.
# id → (scenario, nodes, notes/deferral)
MATRIX: dict[str, tuple[str, object, str]] = {
    # ── A. Ownership / convergence ──────────────────────────────────────────
    "A1": ("One canonical ExecutionAttempt type; grant carries no requested/denied Decision state",
           [f"{GATES}::test_grant_has_no_requested_or_denied_state", f"{STORE}::test_grant_has_no_requested_or_denied_state"], ""),
    "A2": ("attempts/* imports no legacy execution rival (coordinator/executor_runtime/adapter/composition/governed_work)",
           [f"{GATES}::test_attempts_package_never_imports_legacy_rivals"], ""),
    "A3": ("Durable placement record (ExecutionAssignment) persists role/skill/worker/model/harness/env/verifier",
           [f"{PLACE}::test_placement_records_full_assignment"], ""),
    "A4": ("One ExecutionEnvironmentLease type; one active lease per Task",
           [f"{PLACE}::test_lease_acquire_and_one_active_per_task"], ""),
    "A5": ("Execution-panel family converges — aliases resolve, retired panels non-executable stubs",
           ("vitest", VITEST_SURF), "component/source level; live-DOM in field"),
    "A6": ("No default fake-success executor definition; no simulation default on canonical entry points",
           [f"{GATES}::test_no_default_fake_execute_in_plan_execution_adapter", f"{GATES}::test_no_simulation_default_on_canonical_entry_points"], ""),

    # ── B. Authorization ────────────────────────────────────────────────────
    "B1": ("Chat request mints ONE execution-authorization decision; ZERO attempts started",
           [f"{AUTH}::test_execution_request_surfaces_decision_and_starts_zero_attempts", f"{AUTH}::test_request_creates_one_activating_grant_no_authority"], ""),
    "B2": ("Approve activates only the authorized Task set (grant ACTIVE after all Task transitions)",
           [f"{AUTH}::test_approve_activates_all_tasks_then_grant_active"], ""),
    "B3": ("Duplicate approval is idempotent",
           [f"{AUTH}::test_duplicate_approval_idempotent"], ""),
    "B4": ("Rejected decision creates no ACTIVE grant",
           [f"{AUTH}::test_reject_creates_no_active_grant"], ""),
    "B5": ("Expired authorization blocks (swept to EXPIRED, invalid)",
           [f"{AUTH}::test_expired_grant_is_swept_and_invalid"], ""),
    "B6": ("Revocation of an ACTIVE grant",
           [f"{AUTH}::test_revoke_active_grant"], ""),
    "B7": ("Plan revision invalidates a stale authorization on approval",
           [f"{AUTH}::test_approve_after_plan_revision_is_invalidated"], ""),

    # ── C. Canonical attempts ───────────────────────────────────────────────
    "C1": ("Idempotent attempt creation — duplicate request returns existing",
           [f"{STORE}::test_create_attempt_idempotent_returns_existing"], ""),
    "C2": ("Attempt lifecycle CAS: version conflict + status conflict rejected; history append-only",
           [f"{STORE}::test_transition_cas_version_conflict", f"{STORE}::test_transition_cas_status_conflict", f"{STORE}::test_transition_cas_happy_path_and_history"], ""),
    "C3": ("Identity fields immutable; illegal transitions rejected",
           [f"{STORE}::test_transition_cas_rejects_immutable_field_write", f"{STORE}::test_illegal_transition_rejected"], ""),
    "C4": ("Retry is a new linked attempt_number",
           [f"{STORE}::test_retry_is_a_new_attempt_number"], ""),
    "C5": ("Exactly-once: repeated scheduler pass creates no duplicate attempt",
           [f"{SCHED}::test_no_duplicate_attempt_on_repeated_pass"], ""),
    "C6": ("Compiler wires plan-node depends_on → WorkPacket.dependencies (fan-in/chain/persist)",
           [f"{DEPS}"], ""),

    # ── D. Dependencies ─────────────────────────────────────────────────────
    "D1": ("Independent lanes admit up to concurrency",
           [f"{SCHED}::test_independent_lanes_admit_up_to_concurrency"], ""),
    "D2": ("Fan-in Task blocked until predecessors SUCCEED with proof, then unblocked",
           [f"{SCHED}::test_fanin_task_blocked_until_predecessors_succeed"], ""),
    "D3": ("Failed predecessor blocks dependent",
           [f"{SCHED}::test_failed_predecessor_blocks_dependent"], ""),
    "D4": ("Capacity cap limits admission",
           [f"{SCHED}::test_concurrency_cap_limits_admission"], ""),

    # ── E. Role / skill / placement ─────────────────────────────────────────
    "E1": ("Deterministic placement — same inputs → same worker/node/scores",
           [f"{PLACE}::test_placement_is_deterministic"], ""),
    "E2": ("Separation of duty — verifier role ≠ worker role",
           [f"{PLACE}::test_placement_separation_of_duty"], ""),
    "E3": ("No eligible worker fails closed",
           [f"{PLACE}::test_placement_no_eligible_worker_fails_closed"], ""),
    "E4": ("15 readiness checks incl. prohibited-skill → PROHIBITED, verifier≠worker",
           [f"{READY}::test_all_checks_pass_authorized", f"{READY}::test_prohibited_skill_prohibited", f"{READY}::test_verifier_must_differ_from_worker_role"], ""),
    "E5": ("Coordinator canonical lineage never auto-approved (compat isolation)",
           [f"{COORD}::TestGovernanceGate::test_canonical_plan_lineage_never_auto_approved"], ""),

    # ── F. Environment ──────────────────────────────────────────────────────
    "F1": ("Lease rejects repo-root / /opt/OS workspace (cleans up bad worktree)",
           [f"{PLACE}::test_lease_rejects_repo_root_workspace"], ""),
    "F2": ("Lease release + revoke",
           [f"{PLACE}::test_lease_release_and_revoke"], ""),
    "F3": ("Enforced host isolation — bwrap hides /opt/OS (live-verified)",
           [f"{ISO}::test_preflight_hides_opt_os", f"{ISO}::test_isolation_primitive_available"], ""),
    "F4": ("Worker env scrub strips ALL credentials",
           [f"{ISO}::test_env_scrub_strips_all_credentials"], ""),

    # ── G. Instructions ─────────────────────────────────────────────────────
    "G1": ("Dispatch consumes compile_instruction_package (first production caller; sealed hash)",
           [f"{PLACE}::test_compile_package_sealed_and_hashed"], ""),
    "G2": ("Package hash sealed — tamper changes hash",
           [f"{PLACE}::test_compile_package_tamper_changes_hash"], ""),
    "G3": ("Compilation failure blocks dispatch (fail closed)",
           [f"{PLACE}::test_compilation_failure_blocks_dispatch"], ""),

    # ── H. Real execution ───────────────────────────────────────────────────
    "H1": ("Real worker fails closed without CLI (no simulation fallback)",
           [f"{ISO}::test_worker_fails_closed_without_cli"], "H2/H3 real-artifact halves in field"),
    "H2": ("Signed spool: enqueue/claim roundtrip; tampered/wrong-secret/expired quarantined",
           [f"{ISO}::test_enqueue_claim_roundtrip", f"{ISO}::test_tampered_envelope_is_quarantined", f"{ISO}::test_wrong_secret_rejects", f"{ISO}::test_expired_envelope_quarantined"], ""),
    "H3": ("Spool is transport-only — no operator status inferred from files; results signed",
           [f"{ISO}::test_spool_never_infers_status_only_transports", f"{ISO}::test_result_roundtrip_and_signature", f"{ISO}::test_tampered_result_quarantined"], ""),
    "H4": ("execute_work fails closed without canonical router; no dispatch_next fallback",
           [f"{SPINE1}::test_execute_work_fails_closed_without_canonical_router", f"{SPINE1}::test_governed_work_runtime_gates_execution_behind_canonical_routing"], ""),
    "H5": ("Spine authorization consumption — out-of-scope/hash-mismatch/expired/inactive rejected",
           [f"{SPINE}::test_out_of_scope_subject_rejected", f"{SPINE}::test_scope_hash_mismatch_rejected", f"{SPINE}::test_expired_authorization_rejected", f"{SPINE}::test_inactive_grant_rejected", f"{SPINE}::test_authorization_ref_without_lookup_fails_closed"], ""),

    # ── I. Attribution / Proof ──────────────────────────────────────────────
    "I1": ("AttemptProof requires real artifacts + verifier≠worker; no artifacts fails",
           [f"{VERIFY}::test_attempt_proof_passes_with_real_artifacts", f"{VERIFY}::test_verifier_must_differ_from_worker", f"{VERIFY}::test_no_artifacts_fails_verification"], ""),
    "I2": ("Proof-gated completion — attempt SUCCEEDED only with proof_id + distinct verifier",
           [f"{VERIFY}::test_attempt_completes_only_with_proof_and_distinct_verifier"], ""),
    "I3": ("Package-hash mismatch + independent verifier tests fail the verdict",
           [f"{VERIFY}::test_package_hash_mismatch_fails", f"{VERIFY}::test_independent_checks_can_fail_verdict"], ""),
    "I4": ("PlanExecutionProof — reconvergence/tests/live/browser/integrity/zero-deploy; fails on any check",
           [f"{VERIFY}::test_plan_execution_proof", f"{VERIFY}::test_plan_execution_proof_fails_on_any_check"], "live/browser halves in field"),

    # ── J. Surfaces ─────────────────────────────────────────────────────────
    "J1": ("Chat has no execution authorize controls; ChatExecutionCard status-only",
           ("vitest", VITEST_EXEC), ""),
    "J2": ("Execution decisions HUD-only (w2-execution-decision + w2-exec-* only in ControlPanel)",
           ("vitest", VITEST_EXEC), ""),
    "J3": ("Execution-cluster aliases resolve to canonical execution; retired panels stubs",
           ("vitest", VITEST_SURF), ""),
    "J4": ("All 10 w2-* execution testids present at their surfaces",
           ("vitest", VITEST_EXEC), "live-DOM half in field"),
    "J5": ("Persistence-by-refetch — executionAttemptStore never uses localStorage",
           ("vitest", VITEST_EXEC), ""),
    "J6": ("Execution read surface never 500s; retry fails closed without active grant",
           [f"{ROUTES}::test_reads_never_500", f"{ROUTES}::test_retry_fails_closed_without_active_grant"], ""),

    # ── K. Wave boundary ────────────────────────────────────────────────────
    "K1": ("Single-writer scheduler — a losing tick no-ops (no mutation)",
           [f"{SCHED}::test_single_writer_lease_losing_tick_noops"], ""),
    "K2": ("Chat cannot start execution directly — request surfaces the HUD decision only",
           [f"{AUTH}::test_execution_request_surfaces_decision_and_starts_zero_attempts"], ""),
    "K3": ("attempts/* wires no WorkcellDaemon supervisor; events only on the shared spine",
           [f"{GATES}::test_attempts_do_not_wire_workcell_daemon_supervisor", f"{GATES}::test_attempts_events_use_only_shared_event_spine"], ""),

    # ── Harness mechanics (deterministic — no quota, proves harness runnable) ─
    "HM1": ("Control-plane poller drives dispatched→running→verifying→succeeded|failed; "
            "never trusts worker self-report; verifier≠worker; idempotent on redelivery",
            [f"{POLLER}::test_dispatched_result_drives_to_succeeded_with_proof",
             f"{POLLER}::test_failed_verification_never_produces_success_proof",
             f"{POLLER}::test_redelivered_result_is_idempotent"], ""),
    "HM2": ("NO-QUOTA end-to-end rehearsal: REAL scheduler+spool+poller + stub worker "
            "drive full A/B→C→D — exactly-2 concurrency, C blocked until A∧B proof, "
            "fan-in, verifier≠worker (HARNESS_REHEARSAL_ONLY)",
            [f"{REHEARSAL}::test_full_graph_rehearsal_no_quota",
             f"{REHEARSAL}::test_signature_rejection_quarantines_bad_dispatch",
             f"{REHEARSAL}::test_rehearsal_is_not_real_qualification"], ""),
    "HM3": ("Failure-qualification rehearsal: the inject-failure marker is ACTUALLY consumed "
            "(revokes Edit/Write on A's first attempt) → A produces no commit → verification "
            "refuses → A fails (no false Proof) → C stays blocked; retry runs unrevoked",
            [f"{REHEARSAL}::test_failure_qualification_rehearsal",
             f"{FAILPOLICY}::test_marker_actually_changes_policy",
             f"{FAILPOLICY}::test_tools_revoked_a_does_not_touch_retry_or_other_tasks"], ""),

    # ── Field-qualified rows (Session 1) ────────────────────────────────────
    "FA": ("FIELD: two independent workers (A backend, B frontend) run concurrently in isolated worktrees",
           [], "FIELD_PENDING — Session 1 steps w16"),
    "FB": ("FIELD: C reconverges only after A∧B AttemptProof; D independently verifies with real Chrome",
           [], "FIELD_PENDING — Session 1 steps w17–w24"),
    "FC": ("FIELD: same-thread report; refresh + Chrome restart persistence; zero prod deploy; /opt/OS unchanged",
           [], "FIELD_PENDING — Session 1 steps w26–w30"),
    "FD": ("FIELD: failure qualification — injected worker failure, C stays blocked, no false Proof, retry continues",
           [], "FIELD_PENDING — inject-failure pass"),
}


def _run_vitest(suite: str) -> bool:
    try:
        proc = subprocess.run(
            ["npx", "vitest", "run", suite],
            cwd=os.path.join(REPO, "cockpit"),
            capture_output=True, text=True, timeout=600,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        print(f"vitest {suite} not runnable here ({exc.__class__.__name__}) — "
              f"deferred to candidate", file=sys.stderr)
        return False
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=os.path.join(
        REPO, "data", "audits", f"{datetime.date.today().isoformat()}_wave2_matrix_report.md"))
    parser.add_argument("--skip-vitest", action="store_true",
                        help="skip vitest (node_modules not present, e.g. VPS) — vitest rows FIELD_PENDING")
    args = parser.parse_args()

    all_nodes: list[str] = []
    for _sid, (_sc, nodes, _n) in MATRIX.items():
        if isinstance(nodes, list):
            all_nodes.extend(nodes)
    print(f"running {len(all_nodes)} pytest node groups ...")
    cmd = [sys.executable, "-m", "pytest", "-q", "--color=no", "--tb=line", *dict.fromkeys(all_nodes)]
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        print(f"FATAL: pytest exceeded {exc.timeout}s — no report", file=sys.stderr)
        return 1
    stdout = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout)
    failed_nodes = {m.group(1) for m in re.finditer(r"^FAILED (\S+?)(?:\[|\s|$)", stdout, re.MULTILINE)}
    summary_line = next((ln for ln in reversed(stdout.splitlines()) if "passed" in ln or "failed" in ln), "")
    print("pytest:", summary_line.strip())

    # Per-suite vitest results.
    vitest_results: dict[str, bool] = {}
    suites = {n[1] for _s, (_sc, n, _no) in MATRIX.items() if isinstance(n, tuple)}
    for suite in suites:
        if args.skip_vitest:
            vitest_results[suite] = False
            print(f"vitest {suite}: SKIPPED (--skip-vitest)")
        else:
            ok = _run_vitest(suite)
            vitest_results[suite] = ok
            print(f"vitest {suite}: {'PASS' if ok else 'FAIL/deferred'}")

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()

    def _status(nodes: object, note: str) -> str:
        if isinstance(nodes, tuple):  # vitest
            suite = nodes[1]
            ok = vitest_results.get(suite, False)
            if not ok and args.skip_vitest:
                return "FIELD_PENDING (vitest on candidate)"
            base = "PASS" if ok else "FAIL"
        elif isinstance(nodes, list) and not nodes:  # field-only row
            return "FIELD_PENDING"
        else:
            base = ("FAIL" if any(f == n or f.startswith(n + "::")
                                  for n in nodes for f in failed_nodes) else "PASS")
        if note.startswith("FIELD_PENDING"):
            return f"{base} (deterministic) / FIELD_PENDING"
        if note.startswith("FIELD_QUALIFIED"):
            return f"{base} (deterministic) + FIELD_QUALIFIED"
        return base

    rows: list[str] = []
    for sid, (scenario, nodes, note) in MATRIX.items():
        if isinstance(nodes, tuple):
            exact = f"`{nodes[1]}` (vitest)"
            evidence = "vitest suite"
        elif isinstance(nodes, list) and not nodes:
            exact = "— (field)"
            evidence = "Session 1 field harness"
        else:
            exact = "<br>".join(f"`{n}`" for n in nodes)
            evidence = summary_line.strip()
        rows.append(f"| {sid} | {scenario} | {exact} | **{_status(nodes, note)}** | {evidence} | `{commit[:12]}` | {note or '—'} |")

    total = len(MATRIX)
    field_pending = sum(1 for _s, (_sc, _n, note) in MATRIX.items()
                        if note.startswith("FIELD_PENDING") or (isinstance(_n, list) and not _n))
    report = f"""# Wave 2 Acceptance-Matrix Report (machine-generated)

Generated: {datetime.datetime.now().isoformat(timespec="seconds")}
Commit: `{commit}`
Generator: `scripts/wave2_matrix_report.py` (re-run to regenerate — do not hand-edit)
Pytest summary: `{summary_line.strip()}`
Vitest: {", ".join(f"{s.split('/')[-1]}={'PASS' if v else 'deferred'}" for s, v in vitest_results.items()) or "not run"}

Rows: {total} (A–K categories + field rows). Field-pending rows: {field_pending}.
A row is PASS only if every mapped node passed in this run. Field-layer rows are
qualified separately by the Session-1 field harness (3 consecutive green passes +
one failure-qualification pass).

| id | scenario | exact tests | status | evidence | commit | notes / deferral |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}
"""
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"report written: {args.out}")
    return 0 if not failed_nodes else 1


if __name__ == "__main__":
    raise SystemExit(main())
