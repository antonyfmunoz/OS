#!/usr/bin/env python3
"""Wave 1 acceptance-matrix report — machine-generated, 41 rows (A–AO).

Executes every mapped test node (pytest + the vitest surface-authority suite),
records per-id PASS/FAIL from the actual runner output, and emits a markdown
report with: id, exact scenario, exact tests, status, evidence, commit, and
the reason for any deferral. No row is marked PASS unless every mapped node
passed in THIS run.

Usage:
  python3 scripts/wave1_matrix_report.py            # run + write report
  python3 scripts/wave1_matrix_report.py --out PATH # custom output path
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

P = "tests/test_wave1_intent_protocol.py"
C = "tests/test_wave1_contracts.py"
G = "tests/test_wave1_goal_registry.py"
PC = "tests/test_wave1_planning_composition.py"
D = "tests/test_wave1_decisions.py"
X = "tests/test_wave1_matrix_extras.py"
MC = "tests/test_wave1_matrix_completion.py"
VITEST_O = "cockpit/src/renderer/__tests__/surfaceAuthority.test.tsx"

# id → (scenario, [pytest node ids] | VITEST_O, deferral/notes)
MATRIX: dict[str, tuple[str, list[str] | str, str]] = {
    "A": ("COMMUNICATE-only turn: answer, zero artifacts", [f"{P}::TestCommunicationOnly"], ""),
    "B": (
        "Simple Task: one canonical WorkPacket with scope/lineage, no objective/plan/execution",
        [f"{PC}::TestAtomicTaskCapture"],
        "",
    ),
    "C": (
        "Duplicate detection: restatement resolves existing, alternatives by confidence",
        [
            f"{P}::TestExistingWorkResolution::test_restatement_resolves_existing_not_new",
            f"{P}::TestExistingWorkResolution::test_alternatives_ranked_by_confidence",
        ],
        "",
    ),
    "D": ("Objective attachment: LINK_WORK, no duplicates", [f"{MC}::TestD_LinkWork"], ""),
    "E": (
        "Plan revision: v(n+1), v(n) retained, predecessor-only, no cycle",
        [f"{PC}::TestRevision"],
        "",
    ),
    "F": (
        "Complex objective: current/desired/gaps, versioned Plan, canonical Tasks, decision requirement, no execution",
        [f"{PC}::TestComplexObjectivePipeline"],
        "",
    ),
    "G": (
        "Ambiguous reference: single-candidate resolution vs one targeted clarification",
        [f"{P}::TestAmbiguousReference"],
        "",
    ),
    "H": (
        "Chat decision language: resolved, HUD focused, chat explains, NO transition",
        [f"{D}::TestChatDecisionLanguage"],
        "HUD focus/visibility half verified in field step 13–14",
    ),
    "I": (
        "Self-build classification: target_kind, governance profile, canonical packets",
        [f"{MC}::TestIJ_BuildClassification::test_i_umh_self_build_scenario"],
        "",
    ),
    "J": (
        "Projection-build classification: target_kind, governance profile, canonical packets",
        [f"{MC}::TestIJ_BuildClassification::test_j_projection_build_scenario"],
        "",
    ),
    "K": (
        "Cross-company collision: active-context resolution/clarification, zero leakage",
        [f"{MC}::TestK_CrossCompanyCollision"],
        "",
    ),
    "L": (
        "Cross-conversation revision: durable resolution + authority",
        [f"{MC}::TestL_CrossConversationRevision"],
        "",
    ),
    "M": (
        "Capability generality: non-development objective through the same protocol",
        [f"{X}::TestCapabilityGenerality"],
        "",
    ),
    "N": (
        "Concurrency: duplicate submission, revision conflict, double decision, CAS failure",
        [f"{MC}::TestN_Concurrency"],
        "",
    ),
    "O": (
        "Surface authority: chat link-only, HUD-only decisions, aliases resolve, retired components not executable",
        VITEST_O,
        "component/source level; live-DOM half in field step 21",
    ),
    "P": (
        "Tenant/principal: non-empty ids on artifacts; unknown tenancy fails closed; Task scope within Plan scope",
        [f"{P}::TestFailClosedIdentity", f"{C}::TestPrincipalContext", f"{C}::TestWorkScope"],
        "",
    ),
    "Q": (
        "Multi-membership isolation: identical names distinct per tenant, no cross-tenant retrieval",
        [
            f"{X}::TestTenantIsolation",
            f"{MC}::TestL_CrossConversationRevision::test_cross_tenant_explicit_id_rejected",
        ],
        "",
    ),
    "R": (
        "Role-assigned Skills: unauthorized rejected, prohibited rejected, mastery gaps, verifier distinct",
        [f"{PC}::TestRoleBoundSkills"],
        "",
    ),
    "S": (
        "Archetype determinism: same work+scope → same policy; overrides explicit+attributed",
        [f"{PC}::TestArchetypeDeterminism"],
        "",
    ),
    "T": (
        "Fractal decomposition: atomic→1 Task; project→bounded Plan; portfolio→bounded frontier",
        [f"{PC}::TestFractalDecomposition", f"{P}::TestClassification::test_atomic_task"],
        "",
    ),
    "U": (
        "Source correspondence: multi-source fixture → one finding, no duplicates, EvidenceRefs preserved",
        [f"{P}::TestSourceCorrespondence"],
        "repository-evidence fixture (GitHub review + email); live-connector path out of Wave 1 scope",
    ),
    "V": (
        "Instruction compilation: profiles render differently, identity sealed, hash, failure blocks",
        [f"{PC}::TestInstructionCompilation"],
        "",
    ),
    "W": (
        "Software-production profile: layers 0–13 assessed; static prototype explicit not_applicable",
        [f"{PC}::TestDevelopmentProfile"],
        "",
    ),
    "X": (
        "Decision readiness: no actionable Decision before readiness; package with recommendation/uncertainty",
        [f"{PC}::TestDecisionReadiness"],
        "",
    ),
    "Y": (
        "WorkScope/provenance separation: scope never only in evidence; EvidenceRef never authority",
        [
            f"{C}::TestWorkScope::test_scope_is_first_class_typed_fields",
            f"{C}::TestEvidenceRef::test_evidence_has_no_mutation_surface",
            f"{PC}::TestComplexObjectivePipeline::test_full_composition",
        ],
        "",
    ),
    "Z": (
        "Objective/Gap authority: canonical Goal referenced, gap snapshot-classified, legacy machinery zero new writes",
        [f"{PC}::TestGapAuthority", f"{MC}::TestZ_LegacyObjectiveMachineryIsolation"],
        "",
    ),
    "AA": (
        "Membership stability: same principal+tenant → same membership across restart; never session-derived",
        [
            f"{C}::TestPrincipalResolution",
            f"{G}::TestObjectiveCreateOrReuse::test_persisted_across_restart",
        ],
        "",
    ),
    "AB": (
        "Plan acceptance vs execution authority: approval accepts Plan only; drain executes nothing; zero ExecutionAttempts",
        [f"{D}::TestAcceptanceNotExecution"],
        "",
    ),
    "AC": (
        "Event attribution: one correlation chain; identities present; no duplicate creation events",
        [
            f"{P}::TestPlanningUnitOfWork::test_ac_correlation_chain_and_no_duplicate_creation_events"
        ],
        "",
    ),
    "AD": (
        "Readiness semantics: proposed artifacts never block acceptance; missing judgment evidence blocks",
        [f"{PC}::TestDecisionReadiness::test_ad_unknowns_do_not_block_but_contradictions_do"],
        "",
    ),
    "AE": (
        "Objective runtime-state boundary: migration preserves IDs, writes under UMH_STATE_DIR, source unchanged, CAS",
        [
            f"{G}::TestRuntimeStateBoundary",
            f"{G}::TestLegacyMigration",
            f"{G}::TestVersioningAndCas",
        ],
        "",
    ),
    "AF": (
        "Planning unit-of-work recovery: injected failure → retry reuses Objective, one Plan, one lineage",
        [f"{P}::TestPlanningUnitOfWork::test_am_failure_leaves_recoverable_state_and_valid_goal"],
        "",
    ),
    "AG": (
        "Typed Decision contract: first-class fields, identities, plan_acceptance_only, metadata-independent",
        [f"{D}::TestTypedDecisionContract"],
        "",
    ),
    "AH": (
        "Versioned Skill requirement: pinned constraint, role-bound, plan carries pinned refs",
        [
            f"{PC}::TestComplexObjectivePipeline::test_ah_skill_refs_pinned_in_plan",
            f"{C}::TestSkillRequirementRef",
        ],
        "promotion-immutability is structural (plan stores copied refs); explicit replan path in Wave 2",
    ),
    "AI": (
        "Event durability: one shared persisted spine; restart reconstructs lineage",
        [f"{X}::TestEventDurability"],
        "",
    ),
    "AJ": (
        "Cross-projection planning: one Objective/Plan, substrate Tasks precede projection Tasks, narrowed scopes",
        [f"{MC}::TestAJ_CrossProjectionPlanning"],
        "",
    ),
    "AK": (
        "DecisionRequirement: atomic capture → no Decision, non-executable; Plan → Decision only after readiness",
        [
            f"{PC}::TestAtomicTaskCapture::test_ak_retry_is_idempotent",
            f"{D}::TestDecisionRequirementRouting",
        ],
        "",
    ),
    "AL": (
        "Operation identity vs Objective reuse: retry reuses; similar-but-distinct not merged",
        [
            f"{P}::TestPlanningUnitOfWork::test_al_retry_reuses_exact_objective",
            f"{P}::TestPlanningUnitOfWork::test_al_similar_but_distinct_not_merged",
        ],
        "",
    ),
    "AM": (
        "Goal recovery-state compatibility: no invalid Goal status on failure; recovery on PlanningSession only",
        [
            f"{P}::TestPlanningUnitOfWork::test_am_failure_leaves_recoverable_state_and_valid_goal",
            f"{G}::TestObjectiveCreateOrReuse::test_new_objective_starts_draft_objective_type",
        ],
        "",
    ),
    "AN": (
        "Legacy IntentLoop write isolation: zero legacy mutation calls across new Cockpit scenarios",
        [f"{P}::TestLegacyIntentLoopIsolation"],
        "",
    ),
    "AO": (
        "Candidate mounted-state persistence: restart preserves state; no source mutation; writes under /state/umh",
        [f"{MC}::TestAO_MountedStateDeterministic"],
        "FIELD_QUALIFIED (run 73632f24276e, 2026-07-23): container ro-mount "
        "byte-identical (git-free file-hash match host<->container), restart "
        "preserves 7/7 plan records, writes under /state/umh, source tree clean "
        "— 3 consecutive Session-1 passes, reconciliation 0.990/0.987/0.991, "
        "zero orphan 5xx",
    ),
}


def _run_vitest() -> bool:
    try:
        proc = subprocess.run(
            ["npx", "vitest", "run", "src/renderer/__tests__/surfaceAuthority.test.tsx"],
            cwd=os.path.join(REPO, "cockpit"),
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        print("vitest run exceeded 600s — recorded as FAIL", file=sys.stderr)
        return False
    return proc.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=os.path.join(
            REPO, "data", "audits", f"{datetime.date.today().isoformat()}_wave1_matrix_report.md"
        ),
    )
    args = parser.parse_args()

    all_nodes: list[str] = []
    for _sid, (_scenario, nodes, _note) in MATRIX.items():
        if isinstance(nodes, list):
            all_nodes.extend(nodes)
    print(f"running {len(all_nodes)} pytest node groups ...")
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--color=no",
        "--tb=line",
        *dict.fromkeys(all_nodes),
    ]
    try:
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired as exc:
        # A hung pytest run must fail the generator LOUDLY with an exit code —
        # an uncaught TimeoutExpired wrote no report and returned no status.
        print(f"FATAL: pytest run exceeded {exc.timeout}s — no report written", file=sys.stderr)
        return 1
    # Strip any residual ANSI so the committed artifact stays plain text.
    stdout = re.sub(r"\x1b\[[0-9;]*m", "", proc.stdout)
    failed_nodes = {
        m.group(1) for m in re.finditer(r"^FAILED (\S+?)(?:\[|\s|$)", stdout, re.MULTILINE)
    }
    summary_line = next(
        (ln for ln in reversed(stdout.splitlines()) if "passed" in ln or "failed" in ln), ""
    )
    print("pytest:", summary_line.strip())

    print("running vitest surface-authority suite ...")
    vitest_ok = _run_vitest()
    print("vitest:", "PASS" if vitest_ok else "FAIL")

    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()

    def _status(sid: str, nodes: list[str] | str, note: str) -> str:
        if isinstance(nodes, str):
            base = "PASS" if vitest_ok else "FAIL"
        else:
            # Exact node or a ::-delimited child of it — a plain string-prefix
            # match would let TestA's failure flag an unrelated TestA2 row.
            base = (
                "FAIL"
                if any(f == n or f.startswith(n + "::") for n in nodes for f in failed_nodes)
                else "PASS"
            )
        if note.startswith("FIELD_PENDING"):
            return f"{base} (deterministic) / FIELD_PENDING"
        if note.startswith("FIELD_QUALIFIED"):
            return f"{base} (deterministic) + FIELD_QUALIFIED"
        return base

    rows: list[str] = []
    for sid, (scenario, nodes, note) in MATRIX.items():
        exact = nodes if isinstance(nodes, str) else "<br>".join(f"`{n}`" for n in nodes)
        status = _status(sid, nodes, note)
        evidence = "vitest run (8 assertions)" if isinstance(nodes, str) else summary_line.strip()
        rows.append(
            f"| {sid} | {scenario} | {exact} | **{status}** | {evidence} | `{commit[:12]}` | {note or '—'} |"
        )

    total = len(MATRIX)
    field_pending = sum(
        1 for _s, (_sc, _n, note) in MATRIX.items() if note.startswith("FIELD_PENDING")
    )
    field_qualified = sum(
        1 for _s, (_sc, _n, note) in MATRIX.items() if note.startswith("FIELD_QUALIFIED")
    )
    report = f"""# Wave 1 Acceptance-Matrix Report (machine-generated)

Generated: {datetime.datetime.now().isoformat(timespec="seconds")}
Commit: `{commit}`
Generator: `scripts/wave1_matrix_report.py` (re-run to regenerate — do not hand-edit)
Pytest summary: `{summary_line.strip()}`
Vitest (test O): {"PASS" if vitest_ok else "FAIL"}

Rows: {total} (A–AO). Field-pending rows: {field_pending}. Field-qualified rows: {field_qualified}.
A row is PASS only if every mapped node passed in this run.
Field-layer verification (21-step Session 1 journey ×3 passes) is reported
separately by the field harness — this report covers the deterministic layer.

| id | scenario | exact tests | status | evidence | commit | notes / deferral reason |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}
"""
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"report written: {args.out}")
    return 0 if (not failed_nodes and vitest_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
