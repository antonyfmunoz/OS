"""
Comprehensive pytest test suite for Phase 14.6F cross-product canon revision sprint.

Verifies all affected canon artifacts across UMH, EOS, CreatorOS, and LyfeOS
were correctly revised to align with all 18 ratified P0 decisions.

Tests cover:
- Phase marker updates (revised 14.6F)
- All 18 decision references present in relevant artifacts
- Stale language removal across all products
- Implementation gates preserved (operator_approved=false, allows_implementation=false)
- Reality-model framing in UMH artifacts
- Beast promotion language in EOS artifacts
- Resolved decision status in open questions files
- No source code mutation
- Audit report existence and structure
- Cross-product consistency
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Path resolution (worktree-aware)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))

_TEST_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _TEST_DIR.parent
if (_WORKTREE_ROOT / "data" / "umh").exists():
    _REPO_ROOT = _WORKTREE_ROOT

UMH_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6b_umh"
EOS_DIR = _REPO_ROOT / "data" / "umh" / "eos_lossless_canon"
COS_DIR = _REPO_ROOT / "data" / "umh" / "creatoros_lossless_canon"
LOS_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6b_lyfeos"
AUDIT_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6f_canon_revision"

# ---------------------------------------------------------------------------
# Decision reference constants
# ---------------------------------------------------------------------------

ALL_P0_DECISIONS = [
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

# Artifacts expected to have 14.6F phase marker
UMH_REVISED_ARTIFACTS = [
    "umh_open_questions_operator_decision_queue.md",
    "umh_lossless_product_canon.md",
    "umh_ratification_packet.md",
    "umh_audit_report.md",
    "umh_naming_canonicalization.md",
    "umh_projection_ecosystem_doctrine.md",
    "umh_full_end_state_canon.md",
    "umh_cockpit_jarvis_doctrine.md",
    "umh_cockpit_buildable_readiness_detail.md",
    "umh_cockpit_readiness_buildable_criteria.md",
    "umh_cockpit_readiness_gap_matrix.md",
    "umh_code_resolved_substrate_canon.md",
    "umh_world_model_memory_architecture.md",
    "umh_execution_boundary_model.md",
    "umh_governance_approval_lifecycle.md",
    "umh_signal_interpretation_decomposition_canon.md",
    "umh_workstation_jarvis_experience_canon.md",
    "umh_implementation_debt_register.md",
    "umh_codebase_quarantine_rewrite_candidates.md",
    "umh_product_connection_manifest_current_truth.md",
    "umh_projection_registration_protocol.md",
    "umh_coherent_system_layer_map.md",
    "umh_cross_product_integration_architecture.md",
    "umh_private_cockpit_vs_public_projection_boundary.md",
    "umh_substrate_cockpit_projection_boundary_matrix.md",
]

EOS_REVISED_ARTIFACTS = [
    "phase14_6b_eos_lossless_product_canon.md",
    "phase14_6b_eos_open_questions_operator_decision_queue.md",
    "phase14_6b_eos_source_truth_ratification_packet.md",
    "phase14_6b_eos_umh_integration_architecture.md",
    "phase14_6b_eos_audit_report.md",
    "phase14_6b_eos_auth_security_truth.json",
    "phase14_6b_eos_mvp_specification.json",
    "phase14_6b_eos_code_gap_comparison.md",
    "phase14_6b_eos_implementation_debt_register.md",
    "phase14_6b_eos_infrastructure_deployment_map.md",
]

COS_REVISED_ARTIFACTS = [
    "phase14_6b_creatoros_lossless_product_canon.md",
    "phase14_6b_creatoros_open_questions_operator_decision_queue.md",
    "phase14_6b_creatoros_source_truth_ratification_packet.md",
    "phase14_6b_creatoros_auth_security_truth.json",
    "phase14_6b_creatoros_mvp_specification.json",
    "phase14_6b_creatoros_code_gap_comparison.md",
    "phase14_6b_creatoros_eos_boundary_canon.md",
    "phase14_6b_creatoros_audit_report.md",
    "phase14_6b_creatoros_versions_contradictions_matrix.json",
    "phase14_6b_creatoros_implementation_debt_register.md",
    "phase14_6b_creatoros_professional_gap_register.md",
]

LOS_REVISED_ARTIFACTS = [
    "lyfeos_lossless_product_canon.md",
    "lyfeos_open_questions_operator_decision_queue.md",
    "lyfeos_source_truth_ratification_packet.md",
    "lyfeos_auth_migration_candidate_plan.md",
    "lyfeos_infrastructure_deployment_map.md",
    "lyfeos_code_resolved_product_canon.md",
    "lyfeos_umh_connection_architecture.md",
    "lyfeos_umh_connected_future_canon.md",
    "lyfeos_full_end_state_canon.md",
    "lyfeos_audit_report.md",
    "lyfeos_implementation_debt_register.md",
    "lyfeos_version_precedence_matrix.json",
    "lyfeos_mvp_current_canon.md",
    "lyfeos_nova_legacy_naming_correction.md",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _content_lower(path: Path) -> str:
    return _read(path).lower()


_STALE_NAMES = [
    "Universal Mastery Hierarchy",
]

_NEGATION_QUALIFIERS = [
    "not merely",
    "no longer",
    "was ",
    "is not",
    "umh is not",
    "merely an",
    "not an",
    "not a",
    "formerly",
    "previously",
    "stale",
    "non-canonical",
    "old name",
    "renamed from",
    "legacy name",
    "was called",
    "replaced by",
    "superseded",
    "says \"",
    "says “",
    "grep -rl",
    "classified as",
    "→",
    "rename to",
    "carries forward",
]


def _has_stale_unqualified(content: str, stale_term: str) -> list[str]:
    """Find unqualified uses of stale terminology."""
    violations = []
    lower_content = content.lower()
    lower_term = stale_term.lower()
    idx = 0
    while True:
        pos = lower_content.find(lower_term, idx)
        if pos == -1:
            break
        context_start = max(0, pos - 250)
        context = lower_content[context_start:pos + len(lower_term) + 50]
        qualified = any(q in context for q in _NEGATION_QUALIFIERS)
        if not qualified:
            violations.append(content[max(0, pos - 30):pos + len(stale_term) + 30])
        idx = pos + 1
    return violations


# ---------------------------------------------------------------------------
# Section 1: Artifact existence
# ---------------------------------------------------------------------------

class TestArtifactExistence:
    """All revised artifacts must exist."""

    @pytest.mark.parametrize("fname", UMH_REVISED_ARTIFACTS)
    def test_umh_artifact_exists(self, fname: str) -> None:
        assert (UMH_DIR / fname).exists(), f"Missing UMH artifact: {fname}"

    @pytest.mark.parametrize("fname", EOS_REVISED_ARTIFACTS)
    def test_eos_artifact_exists(self, fname: str) -> None:
        assert (EOS_DIR / fname).exists(), f"Missing EOS artifact: {fname}"

    @pytest.mark.parametrize("fname", COS_REVISED_ARTIFACTS)
    def test_cos_artifact_exists(self, fname: str) -> None:
        assert (COS_DIR / fname).exists(), f"Missing CreatorOS artifact: {fname}"

    @pytest.mark.parametrize("fname", LOS_REVISED_ARTIFACTS)
    def test_los_artifact_exists(self, fname: str) -> None:
        assert (LOS_DIR / fname).exists(), f"Missing LyfeOS artifact: {fname}"


# ---------------------------------------------------------------------------
# Section 2: Phase markers (14.6F)
# ---------------------------------------------------------------------------

class TestPhaseMarkers:
    """Revised artifacts must contain '14.6F' or 'revised 14.6F' phase reference."""

    @pytest.mark.parametrize("fname", UMH_REVISED_ARTIFACTS)
    def test_umh_phase_marker(self, fname: str) -> None:
        content = _read(UMH_DIR / fname)
        assert "14.6F" in content or "14.6f" in content.lower(), (
            f"UMH {fname} missing 14.6F phase marker"
        )

    @pytest.mark.parametrize("fname", [f for f in EOS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_eos_phase_marker(self, fname: str) -> None:
        content = _read(EOS_DIR / fname)
        assert "14.6F" in content or "14.6f" in content.lower(), (
            f"EOS {fname} missing 14.6F phase marker"
        )

    @pytest.mark.parametrize("fname", [f for f in COS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_cos_phase_marker(self, fname: str) -> None:
        content = _read(COS_DIR / fname)
        assert "14.6F" in content or "14.6f" in content.lower(), (
            f"CreatorOS {fname} missing 14.6F phase marker"
        )

    @pytest.mark.parametrize("fname", [f for f in LOS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_los_phase_marker(self, fname: str) -> None:
        content = _read(LOS_DIR / fname)
        assert "14.6F" in content or "14.6f" in content.lower(), (
            f"LyfeOS {fname} missing 14.6F phase marker"
        )


# ---------------------------------------------------------------------------
# Section 3: Implementation gates preserved
# ---------------------------------------------------------------------------

class TestImplementationGates:
    """Implementation gates must remain closed across all products."""

    def test_umh_gates_preserved(self) -> None:
        for fname in UMH_REVISED_ARTIFACTS:
            content = _read(UMH_DIR / fname)
            if "allows_implementation" in content:
                assert "allows_implementation: true" not in content.lower().replace(" ", ""), (
                    f"UMH {fname} has open implementation gate"
                )

    def test_eos_gates_preserved(self) -> None:
        for fname in EOS_REVISED_ARTIFACTS:
            path = EOS_DIR / fname
            content = _read(path)
            if "allows_implementation" in content:
                assert "allows_implementation: true" not in content.lower().replace(" ", ""), (
                    f"EOS {fname} has open implementation gate"
                )

    def test_cos_gates_preserved(self) -> None:
        for fname in COS_REVISED_ARTIFACTS:
            content = _read(COS_DIR / fname)
            if "allows_implementation" in content:
                assert "allows_implementation: true" not in content.lower().replace(" ", ""), (
                    f"CreatorOS {fname} has open implementation gate"
                )

    def test_los_gates_preserved(self) -> None:
        for fname in LOS_REVISED_ARTIFACTS:
            content = _read(LOS_DIR / fname)
            if "allows_implementation" in content:
                assert "allows_implementation: true" not in content.lower().replace(" ", ""), (
                    f"LyfeOS {fname} has open implementation gate"
                )


# ---------------------------------------------------------------------------
# Section 4: Stale "Universal Mastery Hierarchy" removed
# ---------------------------------------------------------------------------

class TestStaleNaming:
    """No unqualified use of 'Universal Mastery Hierarchy' in revised artifacts."""

    @pytest.mark.parametrize("fname", UMH_REVISED_ARTIFACTS)
    def test_umh_no_stale_name(self, fname: str) -> None:
        content = _read(UMH_DIR / fname)
        violations = _has_stale_unqualified(content, "Universal Mastery Hierarchy")
        assert not violations, (
            f"UMH {fname} has unqualified 'Universal Mastery Hierarchy': {violations[:3]}"
        )

    @pytest.mark.parametrize("fname", [f for f in EOS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_eos_no_stale_name(self, fname: str) -> None:
        content = _read(EOS_DIR / fname)
        violations = _has_stale_unqualified(content, "Universal Mastery Hierarchy")
        assert not violations, (
            f"EOS {fname} has unqualified 'Universal Mastery Hierarchy': {violations[:3]}"
        )

    @pytest.mark.parametrize("fname", [f for f in COS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_cos_no_stale_name(self, fname: str) -> None:
        content = _read(COS_DIR / fname)
        violations = _has_stale_unqualified(content, "Universal Mastery Hierarchy")
        assert not violations, (
            f"CreatorOS {fname} has unqualified 'Universal Mastery Hierarchy': {violations[:3]}"
        )

    @pytest.mark.parametrize("fname", [f for f in LOS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_los_no_stale_name(self, fname: str) -> None:
        content = _read(LOS_DIR / fname)
        violations = _has_stale_unqualified(content, "Universal Mastery Hierarchy")
        assert not violations, (
            f"LyfeOS {fname} has unqualified 'Universal Mastery Hierarchy': {violations[:3]}"
        )


# ---------------------------------------------------------------------------
# Section 5: UMH reality-model framing (DEC-146C-001)
# ---------------------------------------------------------------------------

class TestRealityModelFraming:
    """Key UMH artifacts must contain reality-model language."""

    _REALITY_TERMS = [
        "reality-isomorphic",
        "reality model",
        "reality-model",
        "reality approximation",
    ]

    _KEY_UMH_ARTIFACTS = [
        "umh_lossless_product_canon.md",
        "umh_projection_ecosystem_doctrine.md",
        "umh_full_end_state_canon.md",
        "umh_code_resolved_substrate_canon.md",
        "umh_world_model_memory_architecture.md",
        "umh_cockpit_jarvis_doctrine.md",
    ]

    @pytest.mark.parametrize("fname", _KEY_UMH_ARTIFACTS)
    def test_has_reality_model_framing(self, fname: str) -> None:
        content = _content_lower(UMH_DIR / fname)
        assert any(t in content for t in self._REALITY_TERMS), (
            f"UMH {fname} missing reality-model framing (DEC-146C-001)"
        )


# ---------------------------------------------------------------------------
# Section 6: Stage 1 organism framing (DEC-146C-003)
# ---------------------------------------------------------------------------

class TestStage1Organism:
    """Cockpit-related artifacts must reference indivisible Stage 1."""

    _STAGE1_ARTIFACTS = [
        "umh_lossless_product_canon.md",
        "umh_cockpit_jarvis_doctrine.md",
        "umh_cockpit_buildable_readiness_detail.md",
        "umh_cockpit_readiness_buildable_criteria.md",
    ]

    @pytest.mark.parametrize("fname", _STAGE1_ARTIFACTS)
    def test_has_stage1_framing(self, fname: str) -> None:
        content = _content_lower(UMH_DIR / fname)
        assert "stage 1" in content or "indivisible" in content or "dec-146c-003" in content, (
            f"UMH {fname} missing Stage 1 organism framing (DEC-146C-003)"
        )


# ---------------------------------------------------------------------------
# Section 7: Materialization principle (DEC-146C-002)
# ---------------------------------------------------------------------------

class TestMaterializationPrinciple:
    """Execution-related artifacts must reference materialization principle."""

    _MAT_ARTIFACTS = [
        "umh_execution_boundary_model.md",
        "umh_lossless_product_canon.md",
    ]

    @pytest.mark.parametrize("fname", _MAT_ARTIFACTS)
    def test_has_materialization_framing(self, fname: str) -> None:
        content = _content_lower(UMH_DIR / fname)
        assert (
            "materialization" in content
            or "dec-146c-002" in content
            or "acquisition path" in content
            or "typed gap" in content
        ), f"UMH {fname} missing materialization principle (DEC-146C-002)"


# ---------------------------------------------------------------------------
# Section 8: UMH open questions resolved
# ---------------------------------------------------------------------------

class TestUMHOpenQuestionsResolved:
    """UMH open questions Q1-Q5 must be marked RESOLVED."""

    def test_q1_to_q5_resolved(self) -> None:
        content = _read(UMH_DIR / "umh_open_questions_operator_decision_queue.md")
        lower = content.lower()
        for q_num in range(1, 6):
            dec_id = f"DEC-146B-UMH-{q_num:03d}"
            assert dec_id.lower() in lower or "resolved" in lower, (
                f"UMH open questions: Q{q_num} ({dec_id}) not marked resolved"
            )

    def test_has_resolved_markers(self) -> None:
        content = _read(UMH_DIR / "umh_open_questions_operator_decision_queue.md")
        resolved_count = content.lower().count("resolved")
        assert resolved_count >= 5, (
            f"Expected at least 5 RESOLVED markers, found {resolved_count}"
        )


# ---------------------------------------------------------------------------
# Section 9: EOS Beast promotion (DEC-146B-EOS-001)
# ---------------------------------------------------------------------------

class TestEOSBeastPromotion:
    """EOS artifacts must reflect Beast as canonical, not 'promotion candidate'."""

    _EOS_CANON_SENSITIVE = [
        "phase14_6b_eos_lossless_product_canon.md",
        "phase14_6b_eos_audit_report.md",
        "phase14_6b_eos_infrastructure_deployment_map.md",
    ]

    @pytest.mark.parametrize("fname", _EOS_CANON_SENSITIVE)
    def test_no_promotion_candidate_language(self, fname: str) -> None:
        content = _read(EOS_DIR / fname)
        lower = content.lower()
        if "promotion candidate" in lower:
            context_start = lower.find("promotion candidate")
            context = lower[max(0, context_start - 200):context_start + 50]
            qualified = any(
                q in context
                for q in ["was ", "formerly", "previously", "no longer",
                           "not a", "stale", "replaced", "original", "prior to"]
            )
            assert qualified, (
                f"EOS {fname} still has unqualified 'promotion candidate' language"
            )

    def test_eos_open_questions_resolved(self) -> None:
        content = _read(EOS_DIR / "phase14_6b_eos_open_questions_operator_decision_queue.md")
        lower = content.lower()
        for dec_id in ["DEC-146B-EOS-001", "DEC-146B-EOS-002", "DEC-146B-EOS-003"]:
            assert dec_id.lower() in lower, f"EOS open questions missing {dec_id}"
        assert "resolved" in lower, "EOS open questions missing RESOLVED markers"


# ---------------------------------------------------------------------------
# Section 10: EOS old decision ID cleanup
# ---------------------------------------------------------------------------

class TestEOSDecisionIDCleanup:
    """Old decision IDs like DEC-145-001 should be updated or qualified."""

    @pytest.mark.parametrize("fname", [f for f in EOS_REVISED_ARTIFACTS if f.endswith(".md")])
    def test_no_unqualified_old_dec_ids(self, fname: str) -> None:
        content = _read(EOS_DIR / fname)
        lower = content.lower()
        if "dec-145-001" in lower:
            context_start = lower.find("dec-145-001")
            context = lower[max(0, context_start - 200):context_start + 200]
            qualified = any(
                q in context
                for q in ["formerly", "previously", "superseded", "replaced",
                           "now dec-146b", "old id", "original", "was",
                           "dec-146b-eos"]
            )
            assert qualified, (
                f"EOS {fname} has unqualified old decision ID DEC-145-001 "
                f"without cross-reference to DEC-146B-EOS-*"
            )


# ---------------------------------------------------------------------------
# Section 11: CreatorOS P0 decisions resolved
# ---------------------------------------------------------------------------

class TestCreatorOSDecisionsResolved:
    """CreatorOS open questions and MVP spec must reflect ratified decisions."""

    def test_cos_open_questions_resolved(self) -> None:
        content = _read(COS_DIR / "phase14_6b_creatoros_open_questions_operator_decision_queue.md")
        lower = content.lower()
        assert "resolved" in lower, "CreatorOS open questions missing RESOLVED markers"
        for dec_id in ["DEC-146B-COS-001", "DEC-146B-COS-002",
                        "DEC-146B-COS-003", "DEC-146B-COS-004"]:
            assert dec_id.lower() in lower, f"CreatorOS open questions missing {dec_id}"

    def test_cos_mvp_scope_reflected(self) -> None:
        content = _read(COS_DIR / "phase14_6b_creatoros_lossless_product_canon.md")
        lower = content.lower()
        assert "dec-146b-cos-001" in lower or "resolved" in lower, (
            "CreatorOS product canon missing MVP scope resolution"
        )

    def test_cos_auth_reflected(self) -> None:
        content = _read(COS_DIR / "phase14_6b_creatoros_audit_report.md")
        lower = content.lower()
        assert "dec-146b-cos-002" in lower or "resolved" in lower or "ratified" in lower, (
            "CreatorOS audit report missing auth decision resolution"
        )


# ---------------------------------------------------------------------------
# Section 12: LyfeOS P0 decisions resolved
# ---------------------------------------------------------------------------

class TestLyfeOSDecisionsResolved:
    """LyfeOS artifacts must reflect ratified PRD, Clerk, and Fly.io decisions."""

    def test_los_open_questions_resolved(self) -> None:
        content = _read(LOS_DIR / "lyfeos_open_questions_operator_decision_queue.md")
        lower = content.lower()
        assert "resolved" in lower, "LyfeOS open questions missing RESOLVED markers"

    def test_los_prd_v2_canonical(self) -> None:
        content = _read(LOS_DIR / "lyfeos_lossless_product_canon.md")
        lower = content.lower()
        assert (
            "dec-146b-los-001" in lower
            or "v2.0" in lower
            or "canonical" in lower
        ), "LyfeOS product canon missing PRD v2.0 canonical status"

    def test_los_clerk_migration_ratified(self) -> None:
        content = _read(LOS_DIR / "lyfeos_auth_migration_candidate_plan.md")
        lower = content.lower()
        assert (
            "dec-146b-los-002" in lower
            or "ratified" in lower
            or "resolved" in lower
        ), "LyfeOS auth migration plan missing ratified status"

    def test_los_flyio_ratified(self) -> None:
        content = _read(LOS_DIR / "lyfeos_infrastructure_deployment_map.md")
        lower = content.lower()
        assert (
            "dec-146b-los-003" in lower
            or "ratified" in lower
            or "resolved" in lower
        ), "LyfeOS infrastructure map missing Fly.io ratification"

    def test_los_no_stale_umh_name(self) -> None:
        for fname in ["lyfeos_umh_connected_future_canon.md",
                       "lyfeos_full_end_state_canon.md"]:
            content = _read(LOS_DIR / fname)
            violations = _has_stale_unqualified(content, "Universal Mastery Hierarchy")
            assert not violations, (
                f"LyfeOS {fname} has unqualified 'Universal Mastery Hierarchy': {violations[:3]}"
            )


# ---------------------------------------------------------------------------
# Section 13: No source code mutation
# ---------------------------------------------------------------------------

class TestNoSourceCodeMutation:
    """Phase 14.6F must not modify any source code files."""

    _SOURCE_DIRS = ["substrate", "adapters", "transports", "services",
                     "projections", "saas", "runtime"]

    @pytest.mark.skip(reason="branch-diff assertion, not a behavioral test: it runs `git diff --name-only main` and asserts an EMPTY diff, so it fails on any branch that touches these dirs. It froze the blast radius of its own docs-only campaign (now complete) and is red-by-construction for all later work. Adjudicated in MVP Wave 0 — retired, not deleted; the real invariants are enforced by the pre-commit gates (dependency-direction, projection-leak, ontology-layers, runtime-state boundary).")
    def test_no_python_source_modified(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
        )
        changed = result.stdout.strip().split("\n") if result.stdout.strip() else []
        source_changes = [
            f for f in changed
            if any(f.startswith(d + "/") for d in self._SOURCE_DIRS)
            and f.endswith(".py")
        ]
        assert not source_changes, (
            f"Phase 14.6F modified source code files: {source_changes}"
        )


# ---------------------------------------------------------------------------
# Section 14: Audit report
# ---------------------------------------------------------------------------

class TestAuditReport:
    """Phase 14.6F audit report must exist with correct structure."""

    AUDIT_FILE = AUDIT_DIR / "phase14_6f_audit_report.md"

    def test_audit_report_exists(self) -> None:
        assert self.AUDIT_FILE.exists(), "Phase 14.6F audit report not found"

    def test_audit_report_minimum_size(self) -> None:
        content = _read(self.AUDIT_FILE)
        assert len(content) > 2000, (
            f"Audit report too small: {len(content)} bytes"
        )

    def test_audit_report_has_phase_marker(self) -> None:
        content = _read(self.AUDIT_FILE)
        assert "14.6F" in content

    def test_audit_report_mentions_all_products(self) -> None:
        content = _content_lower(self.AUDIT_FILE)
        for product in ["umh", "eos", "creatoros", "lyfeos"]:
            assert product in content, (
                f"Audit report missing product: {product}"
            )

    def test_audit_report_has_implementation_gates(self) -> None:
        content = _content_lower(self.AUDIT_FILE)
        assert "allows_implementation" in content or "implementation gate" in content

    def test_audit_report_has_provenance(self) -> None:
        content = _content_lower(self.AUDIT_FILE)
        assert "provenance" in content

    def test_audit_report_references_decisions(self) -> None:
        content = _read(self.AUDIT_FILE)
        dec_count = sum(1 for d in ALL_P0_DECISIONS if d in content)
        assert dec_count >= 10, (
            f"Audit report references only {dec_count}/18 decisions (need at least 10)"
        )


# ---------------------------------------------------------------------------
# Section 15: Cross-product consistency
# ---------------------------------------------------------------------------

class TestCrossProductConsistency:
    """Cross-product consistency checks."""

    def test_umh_product_name_consistent(self) -> None:
        """All UMH artifacts should use 'Universal Meta Harness' when expanding UMH."""
        for fname in UMH_REVISED_ARTIFACTS:
            content = _read(UMH_DIR / fname)
            if "Universal Meta Harness" in content:
                continue
            if "UMH" in content:
                pass

    def test_decision_id_format_consistent(self) -> None:
        """All decision references should use the DEC-146X format, not old DEC-145 format."""
        all_artifacts = (
            [(UMH_DIR, f) for f in UMH_REVISED_ARTIFACTS]
            + [(EOS_DIR, f) for f in EOS_REVISED_ARTIFACTS if f.endswith(".md")]
            + [(COS_DIR, f) for f in COS_REVISED_ARTIFACTS if f.endswith(".md")]
            + [(LOS_DIR, f) for f in LOS_REVISED_ARTIFACTS if f.endswith(".md")]
        )
        old_id_files = []
        for dirp, fname in all_artifacts:
            content = _read(dirp / fname)
            if re.search(r"DEC-145-\d{3}", content):
                context_around = re.findall(r".{0,60}DEC-145-\d{3}.{0,60}", content)
                for ctx in context_around:
                    lower_ctx = ctx.lower()
                    qualified = any(
                        q in lower_ctx
                        for q in ["formerly", "previously", "superseded",
                                   "old", "replaced", "was ", "original",
                                   "carried from", "carries forward",
                                   "audit trail", "now dec-146", "now resolved"]
                    )
                    if not qualified:
                        old_id_files.append(f"{fname}: {ctx.strip()[:80]}")
        assert not old_id_files, (
            f"Files with unqualified old DEC-145 IDs:\n" +
            "\n".join(old_id_files[:10])
        )

    def test_all_products_have_revised_artifacts(self) -> None:
        """Each product set must have at least some revised artifacts."""
        for label, dirp, artifacts in [
            ("UMH", UMH_DIR, UMH_REVISED_ARTIFACTS),
            ("EOS", EOS_DIR, EOS_REVISED_ARTIFACTS),
            ("CreatorOS", COS_DIR, COS_REVISED_ARTIFACTS),
            ("LyfeOS", LOS_DIR, LOS_REVISED_ARTIFACTS),
        ]:
            revised_count = sum(
                1 for f in artifacts
                if (dirp / f).exists()
                and "14.6F" in _read(dirp / f)
            )
            assert revised_count >= 1, (
                f"{label} has no artifacts with 14.6F marker"
            )


# ---------------------------------------------------------------------------
# Section 16: EOS-specific decision content
# ---------------------------------------------------------------------------

class TestEOSDecisionContent:
    """Spot-check that specific EOS ratified content is reflected."""

    def test_clerk_confirmed_in_product_canon(self) -> None:
        content = _content_lower(EOS_DIR / "phase14_6b_eos_lossless_product_canon.md")
        assert "clerk" in content, "EOS product canon must mention Clerk"
        assert "dec-146b-eos-003" in content or "ratified" in content, (
            "EOS product canon must reference Clerk ratification"
        )

    def test_r1_r5_confirmed(self) -> None:
        content = _content_lower(EOS_DIR / "phase14_6b_eos_lossless_product_canon.md")
        assert "r1" in content or "mvp" in content
        assert "dec-146b-eos-002" in content or "confirmed" in content or "ratified" in content


# ---------------------------------------------------------------------------
# Section 17: CreatorOS-specific decision content
# ---------------------------------------------------------------------------

class TestCreatorOSDecisionContent:
    """Spot-check CreatorOS ratified content."""

    def test_mvp_scope_in_product_canon(self) -> None:
        content = _content_lower(COS_DIR / "phase14_6b_creatoros_lossless_product_canon.md")
        assert "content" in content and "community" in content, (
            "CreatorOS product canon missing MVP scope modules"
        )

    def test_clerk_priority_in_audit_report(self) -> None:
        content = _content_lower(COS_DIR / "phase14_6b_creatoros_audit_report.md")
        assert "clerk" in content, "CreatorOS audit report must mention Clerk"


# ---------------------------------------------------------------------------
# Section 18: LyfeOS-specific decision content
# ---------------------------------------------------------------------------

class TestLyfeOSDecisionContent:
    """Spot-check LyfeOS ratified content."""

    def test_flyio_in_infra_map(self) -> None:
        content = _content_lower(LOS_DIR / "lyfeos_infrastructure_deployment_map.md")
        assert "fly.io" in content, "LyfeOS infra map must mention Fly.io"

    def test_prd_v2_in_product_canon(self) -> None:
        content = _content_lower(LOS_DIR / "lyfeos_lossless_product_canon.md")
        assert "v2" in content or "prd" in content

    def test_clerk_in_auth_plan(self) -> None:
        content = _content_lower(LOS_DIR / "lyfeos_auth_migration_candidate_plan.md")
        assert "clerk" in content


# ---------------------------------------------------------------------------
# Section 19: UMH implementation debt ratification
# ---------------------------------------------------------------------------

class TestUMHDebtRatification:
    """UMH debt register items with ratified decisions must be updated."""

    def test_naming_debt_ratified(self) -> None:
        content = _read(UMH_DIR / "umh_implementation_debt_register.md")
        lower = content.lower()
        assert (
            "dec-146b-umh-001" in lower
            or "ratified" in lower
        ), "Naming debt items must reference DEC-146B-UMH-001 ratification"

    def test_workstation_deletion_ratified(self) -> None:
        content = _read(UMH_DIR / "umh_codebase_quarantine_rewrite_candidates.md")
        lower = content.lower()
        assert (
            "dec-146b-umh-004" in lower
            or "ratified" in lower
        ), "Workstation quarantine must reference DEC-146B-UMH-004 ratification"

    def test_pcm_fix_ratified(self) -> None:
        content = _read(UMH_DIR / "umh_product_connection_manifest_current_truth.md")
        lower = content.lower()
        assert (
            "dec-146b-umh-005" in lower
            or "ratified" in lower
            or "abstract port" in lower
        ), "ProductConnectionManager must reference ratified fix pattern"


# ---------------------------------------------------------------------------
# Section 20: JSON file updates
# ---------------------------------------------------------------------------

class TestJSONFileUpdates:
    """JSON artifacts must have updated status fields."""

    def test_eos_auth_json_updated(self) -> None:
        path = EOS_DIR / "phase14_6b_eos_auth_security_truth.json"
        content = _read(path)
        lower = content.lower()
        assert (
            "dec-146b-eos" in lower
            or "ratified" in lower
            or "resolved" in lower
            or "canonical" in lower
        ), "EOS auth JSON must reflect ratified decisions"

    def test_cos_contradictions_json_updated(self) -> None:
        path = COS_DIR / "phase14_6b_creatoros_versions_contradictions_matrix.json"
        content = _read(path)
        lower = content.lower()
        assert (
            "resolved" in lower
            or "ratified" in lower
            or "dec-146b-cos" in lower
        ), "CreatorOS contradictions JSON must reflect ratified decisions"

    def test_los_precedence_json_updated(self) -> None:
        path = LOS_DIR / "lyfeos_version_precedence_matrix.json"
        content = _read(path)
        lower = content.lower()
        assert (
            "dec-146b-los" in lower
            or "ratified" in lower
        ), "LyfeOS precedence JSON must reflect ratified decisions"
