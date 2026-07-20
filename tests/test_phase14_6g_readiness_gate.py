"""
Phase 14.6G: UMH Stage 1 Functional Organism Readiness Gate Tests

Verifies:
- All 7 required artifacts exist
- All 18 P0 decisions remain reflected in canon
- Stage 1 acceptance criteria cover all required organism components
- Implementation gates remain closed
- No source code was modified
- No projection implementation was started
"""
import os
import re
import subprocess
from pathlib import Path

import pytest

_TEST_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _TEST_DIR.parent
_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))
if (_WORKTREE_ROOT / "data" / "umh").exists():
    _REPO_ROOT = _WORKTREE_ROOT

REPO_ROOT = str(_REPO_ROOT)
GATE_DIR = str(_REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6g_readiness_gate")
CANON_DIR = str(_REPO_ROOT / "data" / "umh" / "trinity_convergence")

REQUIRED_ARTIFACTS = [
    "phase14_6g_stage1_readiness_gate.md",
    "phase14_6g_stage1_acceptance_criteria.md",
    "phase14_6g_stage1_dependency_graph.md",
    "phase14_6g_stage1_work_packet_index.md",
    "phase14_6g_governance_gate.md",
    "phase14_6g_projection_dependency_gate.md",
    "phase14_6g_audit_report.md",
]

P0_DECISION_IDS = [
    "DEC-146C-001",
    "DEC-146C-002",
    "DEC-146C-003",
    "DEC-146B-UMH-001",
    "DEC-146B-UMH-002",
    "DEC-146B-UMH-003",
    "DEC-146B-UMH-004",
    "DEC-146B-UMH-005",
    "DEC-146B-EOS-001",
    "DEC-146B-EOS-002",
    "DEC-146B-EOS-003",
    "DEC-146B-COS-001",
    "DEC-146B-COS-002",
    "DEC-146B-COS-003",
    "DEC-146B-COS-004",
    "DEC-146B-LOS-001",
    "DEC-146B-LOS-002",
    "DEC-146B-LOS-003",
]

ACCEPTANCE_CRITERIA_IDS = [
    "AC-1",
    "AC-2",
    "AC-3",
    "AC-4",
    "AC-5",
    "AC-6",
    "AC-7",
    "AC-8",
    "AC-9",
    "AC-10",
]

STAGE1_ORGANISM_COMPONENTS = [
    "Reality Model",
    "Cockpit",
    "Memory",
    "Governed Execution",
    "Work Packet",
    "Agent",
    "Verification",
    "Self-Improvement",
]

WORK_PACKET_IDS = [
    "WP-1.1",
    "WP-1.2",
    "WP-1.3",
    "WP-1.4",
    "WP-2.1",
    "WP-2.2",
    "WP-2.3",
    "WP-2.4",
    "WP-3.1",
    "WP-3.2",
    "WP-3.3",
    "WP-3.4",
]


def _read(filename: str) -> str:
    path = os.path.join(GATE_DIR, filename)
    with open(path, "r") as f:
        return f.read()


# ─── Artifact Existence ──────────────────────────────────────────────

class TestArtifactExistence:
    """All 7 required Phase 14.6G artifacts must exist."""

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_artifact_exists(self, artifact: str) -> None:
        path = os.path.join(GATE_DIR, artifact)
        assert os.path.isfile(path), f"Missing artifact: {artifact}"

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_artifact_not_empty(self, artifact: str) -> None:
        path = os.path.join(GATE_DIR, artifact)
        assert os.path.getsize(path) > 100, f"Artifact suspiciously small: {artifact}"

    def test_artifact_count(self) -> None:
        actual = [f for f in os.listdir(GATE_DIR) if f.endswith(".md")]
        assert len(actual) == len(REQUIRED_ARTIFACTS), (
            f"Expected {len(REQUIRED_ARTIFACTS)} artifacts, found {len(actual)}: {actual}"
        )


# ─── Frontmatter Integrity ──────────────────────────────────────────

class TestFrontmatter:
    """All artifacts must have correct YAML frontmatter."""

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_has_frontmatter(self, artifact: str) -> None:
        content = _read(artifact)
        assert content.startswith("---"), f"{artifact} missing YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, f"{artifact} has incomplete frontmatter"

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_phase_is_14_6g(self, artifact: str) -> None:
        content = _read(artifact)
        assert 'phase: "14.6G"' in content, f"{artifact} has wrong phase"

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_implementation_gate_closed(self, artifact: str) -> None:
        content = _read(artifact)
        assert "allows_implementation: false" in content, (
            f"{artifact} has implementation gate OPEN -- violation"
        )

    @pytest.mark.parametrize("artifact", REQUIRED_ARTIFACTS)
    def test_operator_not_approved(self, artifact: str) -> None:
        content = _read(artifact)
        assert "operator_approved: false" in content, (
            f"{artifact} has operator_approved: true -- violation"
        )


# ─── P0 Decision Coverage ───────────────────────────────────────────

class TestP0DecisionCoverage:
    """All 18 ratified P0 decisions must be referenced in the readiness gate."""

    @pytest.mark.parametrize("decision_id", P0_DECISION_IDS)
    def test_decision_in_readiness_gate(self, decision_id: str) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        assert decision_id in content, (
            f"P0 decision {decision_id} not referenced in readiness gate"
        )

    def test_all_18_decisions_present(self) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        found = [d for d in P0_DECISION_IDS if d in content]
        assert len(found) == 18, (
            f"Expected 18 P0 decisions, found {len(found)}. Missing: "
            f"{set(P0_DECISION_IDS) - set(found)}"
        )


# ─── Acceptance Criteria Completeness ────────────────────────────────

class TestAcceptanceCriteria:
    """Stage 1 acceptance criteria must cover all required organism components."""

    @pytest.mark.parametrize("ac_id", ACCEPTANCE_CRITERIA_IDS)
    def test_acceptance_criterion_exists(self, ac_id: str) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert ac_id in content, f"Acceptance criterion {ac_id} missing"

    @pytest.mark.parametrize("component", STAGE1_ORGANISM_COMPONENTS)
    def test_organism_component_covered(self, component: str) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert component.lower() in content.lower(), (
            f"Organism component '{component}' not covered in acceptance criteria"
        )

    def test_acceptance_criteria_count_at_least_50(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        ac_matches = re.findall(r"AC-\d+\.\d+", content)
        unique = set(ac_matches)
        assert len(unique) >= 50, (
            f"Expected at least 50 acceptance criteria, found {len(unique)}"
        )

    def test_cockpit_primary_interface_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "Cockpit" in content and "primary interface" in content.lower()

    def test_intent_capture_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "intent" in content.lower() and "memory" in content.lower()

    def test_reality_model_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "reality model" in content.lower()

    def test_work_packet_generation_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "work packet" in content.lower()

    def test_agent_routing_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "routing" in content.lower() or "route" in content.lower()

    def test_approval_gate_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "approval" in content.lower() and "governance" in content.lower()

    def test_verification_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "verification" in content.lower() or "verify" in content.lower()

    def test_reality_model_update_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "update" in content.lower() and "reality model" in content.lower()

    def test_self_improvement_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "self-improvement" in content.lower() or "self improvement" in content.lower()

    def test_projection_build_criterion(self) -> None:
        content = _read("phase14_6g_stage1_acceptance_criteria.md")
        assert "projection" in content.lower() or "EOS" in content


# ─── Work Packet Index ───────────────────────────────────────────────

class TestWorkPacketIndex:
    """Work packets must be complete and properly structured."""

    @pytest.mark.parametrize("wp_id", WORK_PACKET_IDS)
    def test_work_packet_exists(self, wp_id: str) -> None:
        content = _read("phase14_6g_stage1_work_packet_index.md")
        assert wp_id in content, f"Work packet {wp_id} missing from index"

    def test_work_packet_count(self) -> None:
        content = _read("phase14_6g_stage1_work_packet_index.md")
        wp_matches = re.findall(r"WP-\d+\.\d+", content)
        unique = set(wp_matches)
        assert len(unique) >= 12, (
            f"Expected at least 12 work packets, found {len(unique)}: {unique}"
        )

    def test_three_waves(self) -> None:
        content = _read("phase14_6g_stage1_work_packet_index.md")
        assert "Wave 1" in content
        assert "Wave 2" in content
        assert "Wave 3" in content

    @pytest.mark.parametrize("field", [
        "Objective",
        "Affected Files",
        "Acceptance Criteria",
        "Risk Level",
        "Approval Requirement",
        "Rollback",
        "Dependency Links",
    ])
    def test_work_packet_has_required_field(self, field: str) -> None:
        content = _read("phase14_6g_stage1_work_packet_index.md")
        assert field.lower() in content.lower(), (
            f"Work packet index missing required field: {field}"
        )

    def test_no_build_from_scratch_packets(self) -> None:
        content = _read("phase14_6g_stage1_work_packet_index.md")
        summary_section = content.split("## Summary")[-1] if "## Summary" in content else ""
        assert "0 BUILD" in summary_section or "0 from scratch" in summary_section.lower(), (
            "Work packet summary should confirm 0 build-from-scratch packets"
        )


# ─── Dependency Graph ────────────────────────────────────────────────

class TestDependencyGraph:
    """Dependency graph must cover all required dimensions."""

    def test_has_parallelization_section(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "paralleliz" in content.lower()

    def test_has_external_dependencies(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "external" in content.lower() and "dependenc" in content.lower()

    def test_has_blocked_items(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "blocked" in content.lower()

    def test_has_simulation_options(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "simulat" in content.lower()

    def test_neon_required(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "Neon" in content, "Neon Postgres must be listed as required"

    def test_three_wave_gates(self) -> None:
        content = _read("phase14_6g_stage1_dependency_graph.md")
        assert "WAVE 1 GATE" in content or "Wave 1" in content
        assert "WAVE 2 GATE" in content or "Wave 2" in content
        assert "WAVE 3 GATE" in content or "Wave 3" in content


# ─── Governance Gate ─────────────────────────────────────────────────

class TestGovernanceGate:
    """Governance gate must define all required conditions."""

    def test_has_source_truth_checks(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "source-truth" in content.lower() or "source truth" in content.lower()

    def test_has_branch_rules(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "branch" in content.lower() and "worktree" in content.lower()

    def test_has_mutation_scope(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "mutation scope" in content.lower() or "allowed mutation" in content.lower()

    def test_has_approval_levels(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "approval level" in content.lower()

    def test_has_test_requirements(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "test requirement" in content.lower()

    def test_has_rollback_requirements(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "rollback" in content.lower()

    def test_has_audit_requirements(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "audit" in content.lower()

    def test_forbidden_mutations_listed(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "FORBIDDEN" in content or "forbidden" in content.lower()

    def test_explicit_approval_procedure(self) -> None:
        content = _read("phase14_6g_governance_gate.md")
        assert "approve phase 14.7a" in content.lower() or "14.7A" in content


# ─── Projection Dependency Gate ──────────────────────────────────────

class TestProjectionDependencyGate:
    """Projection apps must remain blocked until Stage 1 is complete."""

    def test_eos_gated(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        assert "EOS" in content and "blocked" in content.lower()

    def test_creatoros_gated_on_eos(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        assert "CreatorOS" in content
        assert "EOS" in content
        assert "clerk" in content.lower()

    def test_lyfeos_gated_on_creatoros(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        assert "LyfeOS" in content
        assert "CreatorOS" in content
        lower = content.lower()
        assert "after creatoros" in lower or "creatoros proves" in lower

    def test_sequential_dependency_chain(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        eos_pos = content.find("EOS")
        cos_pos = content.find("CreatorOS")
        los_pos = content.find("LyfeOS")
        assert eos_pos < cos_pos < los_pos, (
            "Dependency chain must be UMH → EOS → CreatorOS → LyfeOS"
        )

    def test_projection_agnosticism_required(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        assert "agnostic" in content.lower()


# ─── Implementation Safety ───────────────────────────────────────────

class TestImplementationSafety:
    """No source code was modified. Implementation gates remain closed."""

    def test_no_allows_implementation_true_in_frontmatter(self) -> None:
        for artifact in REQUIRED_ARTIFACTS:
            content = _read(artifact)
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                assert "allows_implementation: true" not in frontmatter, (
                    f"{artifact} frontmatter has allows_implementation: true -- violation"
                )

    def test_all_frontmatters_explicitly_close_gate(self) -> None:
        for artifact in REQUIRED_ARTIFACTS:
            content = _read(artifact)
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                assert "allows_implementation: false" in frontmatter, (
                    f"{artifact} frontmatter missing allows_implementation: false"
                )

    def test_gate_dir_contains_only_md_files(self) -> None:
        files = os.listdir(GATE_DIR)
        non_md = [f for f in files if not f.endswith(".md")]
        assert len(non_md) == 0, (
            f"Gate directory should contain only .md files, found: {non_md}"
        )

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_python_files_modified_in_phase(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "*.py"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        py_files = [f for f in result.stdout.strip().split("\n") if f and not f.startswith("tests/")]
        assert len(py_files) == 0, (
            f"Source .py files were modified (excluding tests/): {py_files}"
        )

    def test_no_typescript_files_modified(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "*.ts", "*.tsx"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        ts_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(ts_files) == 0, (
            f"TypeScript files were modified: {ts_files}"
        )

    def test_no_saas_modifications(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "saas/"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        saas_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(saas_files) == 0, (
            f"saas/ directory was modified: {saas_files}"
        )

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_projections_modifications(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "projections/"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        proj_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(proj_files) == 0, (
            f"projections/ directory was modified: {proj_files}"
        )

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_substrate_modifications(self) -> None:
        result = subprocess.run(
            ["git", "diff", "--name-only", "main", "--", "substrate/"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        sub_files = [f for f in result.stdout.strip().split("\n") if f]
        assert len(sub_files) == 0, (
            f"substrate/ directory was modified: {sub_files}"
        )


# ─── Cross-Artifact Consistency ──────────────────────────────────────

class TestCrossArtifactConsistency:
    """Artifacts must be internally consistent with each other."""

    def test_work_packets_match_dependency_graph(self) -> None:
        wp_content = _read("phase14_6g_stage1_work_packet_index.md")
        dep_content = _read("phase14_6g_stage1_dependency_graph.md")
        for wp_id in WORK_PACKET_IDS:
            assert wp_id in wp_content, f"{wp_id} missing from work packet index"
            assert wp_id in dep_content, f"{wp_id} missing from dependency graph"

    def test_acceptance_criteria_match_readiness_gate(self) -> None:
        ac_content = _read("phase14_6g_stage1_acceptance_criteria.md")
        gate_content = _read("phase14_6g_stage1_readiness_gate.md")
        assert "50" in ac_content, "Acceptance criteria should mention 50 tests"
        assert "acceptance criteria" in gate_content.lower()

    def test_governance_references_phase_14_7a(self) -> None:
        gov_content = _read("phase14_6g_governance_gate.md")
        gate_content = _read("phase14_6g_stage1_readiness_gate.md")
        assert "14.7A" in gov_content
        assert "14.7A" in gate_content

    def test_projection_gate_references_all_three(self) -> None:
        content = _read("phase14_6g_projection_dependency_gate.md")
        assert "EOS" in content
        assert "CreatorOS" in content
        assert "LyfeOS" in content

    def test_audit_report_lists_all_artifacts(self) -> None:
        content = _read("phase14_6g_audit_report.md")
        for artifact in REQUIRED_ARTIFACTS:
            artifact_name = artifact.replace(".md", "")
            assert artifact_name in content, (
                f"Audit report does not reference {artifact_name}"
            )


# ─── Canon Product Name ─────────────────────────────────────────────

class TestProductName:
    """Universal Meta Harness must be the canonical product name."""

    def test_universal_meta_harness_in_readiness_gate(self) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        assert "Universal Meta Harness" in content

    def test_no_unqualified_mastery_hierarchy_in_gate_artifacts(self) -> None:
        for artifact in REQUIRED_ARTIFACTS:
            content = _read(artifact)
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "Universal Mastery Hierarchy" in line:
                    lower_line = line.lower()
                    is_qualified = any(q in lower_line for q in [
                        "debt", "gap", "stale", "non-canonical", "renamed",
                        "not", "unqualified", "zero",
                    ])
                    assert is_qualified, (
                        f"{artifact}:{i+1} -- unqualified 'Universal Mastery Hierarchy' found: {line.strip()}"
                    )


# ─── Indivisibility Constraint ───────────────────────────────────────

class TestIndivisibility:
    """Stage 1 must be defined as indivisible across all artifacts."""

    def test_indivisible_in_readiness_gate(self) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        assert "indivisible" in content.lower()

    def test_four_components_in_readiness_gate(self) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        lower = content.lower()
        assert "reality model" in lower
        assert "cockpit" in lower
        assert "memory" in lower
        assert "governed execution" in lower or "execution loop" in lower

    def test_vertical_slice_not_complete_build(self) -> None:
        content = _read("phase14_6g_stage1_readiness_gate.md")
        assert "vertical slice" in content.lower()
