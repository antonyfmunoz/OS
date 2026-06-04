"""
Comprehensive pytest test suite for Phase 14.6D canon revision.

Verifies all 17 UMH canon artifacts were correctly revised to align
with ratified DEC-146C-001/002/003 decisions. Tests cover:
- Artifact existence and minimum size
- Phase marker updates (revised 14.6D)
- DEC-146C decision references
- Reality-model framing presence
- Stale language removal (orchestration kernel)
- Product name preservation (Universal Meta Harness)
- Implementation gate preservation (operator_approved=false, allows_implementation=false)
- Stage 1 organism framing
- Materialization principle integration
- Audit report existence and structure
- No source code mutation
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))

# When running from a worktree, resolve paths relative to the test file location
_TEST_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _TEST_DIR.parent
if (_WORKTREE_ROOT / "data" / "umh").exists():
    _REPO_ROOT = _WORKTREE_ROOT
CANON_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6b_umh"
AUDIT_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6d_canon_revision"

REVISED_MD_ARTIFACTS: list[str] = [
    "umh_lossless_product_canon",
    "umh_projection_ecosystem_doctrine",
    "umh_full_end_state_canon",
    "umh_cockpit_jarvis_doctrine",
    "umh_cockpit_buildable_readiness_detail",
    "umh_cockpit_readiness_buildable_criteria",
    "umh_cockpit_readiness_gap_matrix",
    "umh_private_cockpit_vs_public_projection_boundary",
    "umh_substrate_cockpit_projection_boundary_matrix",
    "umh_world_model_memory_architecture",
    "umh_execution_boundary_model",
    "umh_governance_approval_lifecycle",
    "umh_code_resolved_substrate_canon",
    "umh_workstation_jarvis_experience_canon",
    "umh_signal_interpretation_decomposition_canon",
    "umh_naming_canonicalization",
]

REVISED_JSON_ARTIFACTS: list[str] = [
    "umh_cockpit_screen_panel_inventory",
]

ALL_REVISED_ARTIFACTS: list[str] = REVISED_MD_ARTIFACTS + REVISED_JSON_ARTIFACTS

MIN_LINE_COUNTS: dict[str, int] = {
    "umh_lossless_product_canon": 50,
    "umh_projection_ecosystem_doctrine": 50,
    "umh_full_end_state_canon": 50,
    "umh_cockpit_jarvis_doctrine": 50,
    "umh_cockpit_buildable_readiness_detail": 30,
    "umh_cockpit_readiness_buildable_criteria": 20,
    "umh_cockpit_readiness_gap_matrix": 20,
    "umh_cockpit_screen_panel_inventory": 20,
    "umh_private_cockpit_vs_public_projection_boundary": 20,
    "umh_substrate_cockpit_projection_boundary_matrix": 30,
    "umh_world_model_memory_architecture": 50,
    "umh_execution_boundary_model": 50,
    "umh_governance_approval_lifecycle": 50,
    "umh_code_resolved_substrate_canon": 30,
    "umh_workstation_jarvis_experience_canon": 50,
    "umh_signal_interpretation_decomposition_canon": 30,
    "umh_naming_canonicalization": 30,
}

DEC_REFERENCES = ["DEC-146C-001", "DEC-146C-002", "DEC-146C-003"]

REALITY_MODEL_TERMS: list[str] = [
    r"reality[- ]?model",
    r"reality[- ]?isomorphic",
    r"12[- ]layer",
]

STALE_IDENTITY_TERMS: list[str] = [
    r"orchestration kernel",
]

STAGE1_TERMS: list[str] = [
    r"Stage\s*1",
    r"indivisible",
    r"Reality\s+Model\s*\+\s*Cockpit\s*\+\s*Memory\s*\+\s*Governed\s+Execution\s+Loop",
]

MATERIALIZATION_TERMS: list[str] = [
    r"materialization\s+principle",
    r"typed\s+gap",
    r"acquisition\s+path",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _md_path(slug: str) -> Path:
    return CANON_DIR / f"{slug}.md"


def _json_path(slug: str) -> Path:
    return CANON_DIR / f"{slug}.json"


def _load_md(slug: str) -> str:
    path = _md_path(slug)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _load_json(slug: str) -> dict:
    path = _json_path(slug)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_md_lines(slug: str) -> list[str]:
    return _load_md(slug).splitlines()


def _parse_md_frontmatter(content: str) -> Dict[str, Any]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    try:
        end_idx = content.index("---", 3)
    except ValueError:
        return {}
    frontmatter_text = content[3:end_idx].strip()
    result: Dict[str, Any] = {}
    for line in frontmatter_text.split("\n"):
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            result[key] = value
    return result


def _md_has_text(content: str, pattern: str, flags: int = re.IGNORECASE) -> bool:
    return bool(re.search(pattern, content, flags))


def _md_has_section(content: str, heading_pattern: str) -> bool:
    for line in content.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if re.search(heading_pattern, line, re.IGNORECASE):
                return True
    return False


def _count_occurrences(content: str, pattern: str, flags: int = re.IGNORECASE) -> int:
    return len(re.findall(pattern, content, flags))


# ---------------------------------------------------------------------------
# 1. TestArtifactExistence — all 17 revised artifacts exist
# ---------------------------------------------------------------------------

class TestArtifactExistence:
    """Every revised artifact file must exist on disk."""

    @pytest.mark.parametrize("slug", REVISED_MD_ARTIFACTS)
    def test_md_artifact_exists(self, slug: str) -> None:
        path = _md_path(slug)
        assert path.exists(), f"Missing MD artifact: {path}"

    @pytest.mark.parametrize("slug", REVISED_JSON_ARTIFACTS)
    def test_json_artifact_exists(self, slug: str) -> None:
        path = _json_path(slug)
        assert path.exists(), f"Missing JSON artifact: {path}"

    def test_artifact_count(self) -> None:
        assert len(ALL_REVISED_ARTIFACTS) == 17, "Expected exactly 17 revised artifacts"


# ---------------------------------------------------------------------------
# 2. TestMinimumSize — artifacts are non-trivially sized
# ---------------------------------------------------------------------------

class TestMinimumSize:

    @pytest.mark.parametrize("slug", REVISED_MD_ARTIFACTS)
    def test_md_minimum_lines(self, slug: str) -> None:
        lines = _load_md_lines(slug)
        minimum = MIN_LINE_COUNTS.get(slug, 20)
        assert len(lines) >= minimum, (
            f"{slug} has {len(lines)} lines, expected >= {minimum}"
        )

    @pytest.mark.parametrize("slug", REVISED_JSON_ARTIFACTS)
    def test_json_minimum_lines(self, slug: str) -> None:
        path = _json_path(slug)
        with open(path, "r") as fh:
            lines = fh.readlines()
        minimum = MIN_LINE_COUNTS.get(slug, 20)
        assert len(lines) >= minimum, (
            f"{slug} has {len(lines)} lines, expected >= {minimum}"
        )


# ---------------------------------------------------------------------------
# 3. TestPhaseMarkerUpdated — all artifacts show "revised 14.6D"
# ---------------------------------------------------------------------------

class TestPhaseMarkerUpdated:
    """Every revised artifact must contain 'revised 14.6D' in its phase marker."""

    @pytest.mark.parametrize("slug", REVISED_MD_ARTIFACTS)
    def test_md_phase_marker(self, slug: str) -> None:
        content = _load_md(slug)
        assert _md_has_text(content, r"revised\s+14\.6D"), (
            f"{slug} missing 'revised 14.6D' phase marker"
        )

    @pytest.mark.parametrize("slug", REVISED_JSON_ARTIFACTS)
    def test_json_phase_marker(self, slug: str) -> None:
        data = _load_json(slug)
        phase_val = data.get("phase", "")
        assert "revised 14.6D" in phase_val, (
            f"{slug} JSON phase field missing 'revised 14.6D'"
        )


# ---------------------------------------------------------------------------
# 4. TestDecisionReferences — DEC-146C-001/002/003 cited where appropriate
# ---------------------------------------------------------------------------

class TestDecisionReferences:
    """Artifacts must reference the ratified decisions they incorporate."""

    ARTIFACTS_MUST_CITE_001: list[str] = [
        "umh_lossless_product_canon",
        "umh_projection_ecosystem_doctrine",
        "umh_full_end_state_canon",
        "umh_cockpit_jarvis_doctrine",
        "umh_world_model_memory_architecture",
        "umh_code_resolved_substrate_canon",
        "umh_workstation_jarvis_experience_canon",
        "umh_signal_interpretation_decomposition_canon",
        "umh_naming_canonicalization",
        "umh_substrate_cockpit_projection_boundary_matrix",
    ]

    ARTIFACTS_MUST_CITE_002: list[str] = [
        "umh_projection_ecosystem_doctrine",
        "umh_full_end_state_canon",
        "umh_execution_boundary_model",
        "umh_governance_approval_lifecycle",
    ]

    ARTIFACTS_MUST_CITE_003: list[str] = [
        "umh_lossless_product_canon",
        "umh_cockpit_jarvis_doctrine",
        "umh_cockpit_buildable_readiness_detail",
        "umh_cockpit_readiness_buildable_criteria",
        "umh_cockpit_readiness_gap_matrix",
        "umh_world_model_memory_architecture",
        "umh_workstation_jarvis_experience_canon",
    ]

    @pytest.mark.parametrize("slug", ARTIFACTS_MUST_CITE_001)
    def test_cites_dec_001(self, slug: str) -> None:
        content = _load_md(slug)
        assert _md_has_text(content, r"DEC-146C-001"), (
            f"{slug} must cite DEC-146C-001"
        )

    @pytest.mark.parametrize("slug", ARTIFACTS_MUST_CITE_002)
    def test_cites_dec_002(self, slug: str) -> None:
        content = _load_md(slug)
        assert _md_has_text(content, r"DEC-146C-002"), (
            f"{slug} must cite DEC-146C-002"
        )

    @pytest.mark.parametrize("slug", ARTIFACTS_MUST_CITE_003)
    def test_cites_dec_003(self, slug: str) -> None:
        content = _load_md(slug)
        assert _md_has_text(content, r"DEC-146C-003"), (
            f"{slug} must cite DEC-146C-003"
        )


# ---------------------------------------------------------------------------
# 5. TestRealityModelFraming — reality-model language present
# ---------------------------------------------------------------------------

class TestRealityModelFraming:
    """All 17 artifacts must contain reality-model framing language."""

    @pytest.mark.parametrize("slug", REVISED_MD_ARTIFACTS)
    def test_md_has_reality_model_language(self, slug: str) -> None:
        content = _load_md(slug)
        found_any = any(
            _md_has_text(content, term) for term in REALITY_MODEL_TERMS
        )
        assert found_any, (
            f"{slug} lacks reality-model framing language "
            f"(none of: {REALITY_MODEL_TERMS})"
        )

    @pytest.mark.parametrize("slug", REVISED_JSON_ARTIFACTS)
    def test_json_has_reality_model_language(self, slug: str) -> None:
        raw = _json_path(slug).read_text(encoding="utf-8")
        found_any = any(
            bool(re.search(term, raw, re.IGNORECASE))
            for term in REALITY_MODEL_TERMS
        )
        assert found_any, (
            f"{slug} JSON lacks reality-model framing language"
        )


# ---------------------------------------------------------------------------
# 6. TestStaleLanguageRemoved — "orchestration kernel" not in identity sections
# ---------------------------------------------------------------------------

class TestStaleLanguageRemoved:
    """Stale identity framing must not appear as the primary identity."""

    IDENTITY_ARTIFACTS: list[str] = [
        "umh_lossless_product_canon",
        "umh_projection_ecosystem_doctrine",
        "umh_full_end_state_canon",
        "umh_workstation_jarvis_experience_canon",
    ]

    @pytest.mark.parametrize("slug", IDENTITY_ARTIFACTS)
    def test_no_orchestration_kernel_as_identity(self, slug: str) -> None:
        content = _load_md(slug)
        for term in STALE_IDENTITY_TERMS:
            matches = list(re.finditer(term, content, re.IGNORECASE))
            for match in matches:
                ctx_start = max(0, match.start() - 200)
                ctx = content[ctx_start:match.end() + 200].lower()
                negation_qualifiers = [
                    "not merely", "no longer", "was", "is not",
                    "umh is not", "merely an", "not an", "not a",
                ]
                has_qualifier = any(q in ctx for q in negation_qualifiers)
                assert has_qualifier, (
                    f"{slug} uses '{match.group()}' without negation qualifier — "
                    f"this appears to be stale identity framing. Context: ...{ctx}..."
                )


# ---------------------------------------------------------------------------
# 7. TestProductNamePreserved — "Universal Meta Harness" still present
# ---------------------------------------------------------------------------

class TestProductNamePreserved:

    def test_naming_canon_has_product_name(self) -> None:
        content = _load_md("umh_naming_canonicalization")
        assert _md_has_text(content, r"Universal Meta Harness"), (
            "Naming canon missing 'Universal Meta Harness'"
        )

    def test_naming_canon_no_engine_rename(self) -> None:
        content = _load_md("umh_naming_canonicalization")
        assert _md_has_text(content, r"do not rename to .engine"), (
            "Naming canon missing 'do not rename to engine' rule"
        )

    def test_naming_canon_functional_descriptor(self) -> None:
        content = _load_md("umh_naming_canonicalization")
        assert _md_has_text(content, r"functional descriptor.*not.*product name"), (
            "Naming canon missing clarification that 'reality-isomorphic intelligence harness' "
            "is a functional descriptor, not a product name"
        )

    def test_product_canon_has_product_name(self) -> None:
        content = _load_md("umh_lossless_product_canon")
        assert _md_has_text(content, r"Universal Meta Harness"), (
            "Product canon missing 'Universal Meta Harness'"
        )


# ---------------------------------------------------------------------------
# 8. TestImplementationGatesPreserved — no gates opened
# ---------------------------------------------------------------------------

class TestImplementationGatesPreserved:
    """operator_approved and allows_implementation must remain false."""

    FRONTMATTER_ARTIFACTS: list[str] = [
        "umh_lossless_product_canon",
        "umh_projection_ecosystem_doctrine",
        "umh_cockpit_jarvis_doctrine",
        "umh_execution_boundary_model",
        "umh_governance_approval_lifecycle",
    ]

    @pytest.mark.parametrize("slug", FRONTMATTER_ARTIFACTS)
    def test_operator_approved_false(self, slug: str) -> None:
        content = _load_md(slug)
        fm = _parse_md_frontmatter(content)
        if "operator_approved" in fm:
            assert fm["operator_approved"] is False, (
                f"{slug} has operator_approved != false"
            )

    @pytest.mark.parametrize("slug", FRONTMATTER_ARTIFACTS)
    def test_allows_implementation_false(self, slug: str) -> None:
        content = _load_md(slug)
        fm = _parse_md_frontmatter(content)
        if "allows_implementation" in fm:
            assert fm["allows_implementation"] is False, (
                f"{slug} has allows_implementation != false"
            )

    def test_no_artifact_has_approved_true(self) -> None:
        for slug in REVISED_MD_ARTIFACTS:
            content = _load_md(slug)
            fm = _parse_md_frontmatter(content)
            assert fm.get("operator_approved") is not True, (
                f"{slug} has operator_approved = true — gate violation!"
            )

    def test_no_artifact_allows_implementation(self) -> None:
        for slug in REVISED_MD_ARTIFACTS:
            content = _load_md(slug)
            fm = _parse_md_frontmatter(content)
            assert fm.get("allows_implementation") is not True, (
                f"{slug} has allows_implementation = true — gate violation!"
            )

    def test_all_status_draft(self) -> None:
        for slug in REVISED_MD_ARTIFACTS:
            content = _load_md(slug)
            upper = content[:500].upper()
            assert "DRAFT" in upper, (
                f"{slug} does not contain DRAFT status in header"
            )


# ---------------------------------------------------------------------------
# 9. TestStage1OrganismFraming — indivisible organism language present
# ---------------------------------------------------------------------------

class TestStage1OrganismFraming:
    """Key artifacts must contain Stage 1 organism framing."""

    STAGE1_ARTIFACTS: list[str] = [
        "umh_lossless_product_canon",
        "umh_cockpit_jarvis_doctrine",
        "umh_cockpit_buildable_readiness_detail",
        "umh_cockpit_readiness_buildable_criteria",
        "umh_cockpit_readiness_gap_matrix",
        "umh_world_model_memory_architecture",
        "umh_workstation_jarvis_experience_canon",
    ]

    @pytest.mark.parametrize("slug", STAGE1_ARTIFACTS)
    def test_has_stage1_reference(self, slug: str) -> None:
        content = _load_md(slug)
        assert _md_has_text(content, r"Stage\s*1"), (
            f"{slug} missing Stage 1 reference"
        )

    @pytest.mark.parametrize("slug", STAGE1_ARTIFACTS)
    def test_has_organism_language(self, slug: str) -> None:
        content = _load_md(slug)
        has_organism = _md_has_text(content, r"organism")
        has_indivisible = _md_has_text(content, r"indivisible")
        assert has_organism or has_indivisible, (
            f"{slug} missing organism/indivisible language"
        )

    def test_cockpit_doctrine_has_acceptance_criteria(self) -> None:
        content = _load_md("umh_cockpit_jarvis_doctrine")
        assert _md_has_text(content, r"acceptance\s+criteria"), (
            "Cockpit doctrine missing 'acceptance criteria'"
        )

    def test_cockpit_doctrine_has_readiness_gate(self) -> None:
        content = _load_md("umh_cockpit_jarvis_doctrine")
        assert _md_has_section(content, r"Stage\s*1\s*Organism\s*Readiness"), (
            "Cockpit doctrine missing 'Stage 1 Organism Readiness' section"
        )

    def test_buildable_readiness_has_component_tags(self) -> None:
        content = _load_md("umh_cockpit_buildable_readiness_detail")
        for tag in ["RM", "CK", "MM", "GE"]:
            assert tag in content, (
                f"Buildable readiness detail missing component tag {tag}"
            )


# ---------------------------------------------------------------------------
# 10. TestMaterializationPrinciple — DEC-146C-002 integration
# ---------------------------------------------------------------------------

class TestMaterializationPrinciple:

    MATERIALIZATION_ARTIFACTS: list[str] = [
        "umh_projection_ecosystem_doctrine",
        "umh_full_end_state_canon",
        "umh_execution_boundary_model",
    ]

    @pytest.mark.parametrize("slug", MATERIALIZATION_ARTIFACTS)
    def test_has_materialization_principle(self, slug: str) -> None:
        content = _load_md(slug)
        found_any = any(
            _md_has_text(content, term) for term in MATERIALIZATION_TERMS
        )
        assert found_any, (
            f"{slug} missing materialization principle language"
        )

    def test_execution_boundary_has_gap_taxonomy(self) -> None:
        content = _load_md("umh_execution_boundary_model")
        gap_types = [
            "IMPOSSIBLE", "ILLEGAL", "UNSAFE", "UNAVAILABLE",
            "UNDER_RESOURCED", "UNPROVEN", "NOT_YET_ACQUIRED", "TIME_BOUND",
        ]
        for gap_type in gap_types:
            assert gap_type in content, (
                f"Execution boundary model missing gap type: {gap_type}"
            )

    def test_governance_has_mutation_governance(self) -> None:
        content = _load_md("umh_governance_approval_lifecycle")
        assert _md_has_text(content, r"reality[- ]?model\s+mutation"), (
            "Governance lifecycle missing reality-model mutation governance"
        )


# ---------------------------------------------------------------------------
# 11. TestProjectionReframing — projections as instance reality models
# ---------------------------------------------------------------------------

class TestProjectionReframing:

    def test_ecosystem_doctrine_instance_reality_models(self) -> None:
        content = _load_md("umh_projection_ecosystem_doctrine")
        assert _md_has_text(content, r"instance\s+reality\s+model"), (
            "Ecosystem doctrine missing 'instance reality model' framing"
        )

    def test_boundary_matrix_reality_model_scope(self) -> None:
        content = _load_md("umh_substrate_cockpit_projection_boundary_matrix")
        assert _md_has_text(content, r"reality\s+model\s+infrastructure"), (
            "Boundary matrix missing 'Reality Model Infrastructure'"
        )
        assert _md_has_text(content, r"reality\s+model\s+rendering"), (
            "Boundary matrix missing 'Reality Model Rendering'"
        )
        assert _md_has_text(content, r"instance\s+reality\s+model"), (
            "Boundary matrix missing 'Instance Reality Models'"
        )

    def test_private_vs_public_boundary_reframed(self) -> None:
        content = _load_md("umh_private_cockpit_vs_public_projection_boundary")
        assert _md_has_text(content, r"reality[- ]?model"), (
            "Private vs public boundary missing reality-model framing"
        )


# ---------------------------------------------------------------------------
# 12. TestAuditReport — 14.6D audit report exists and has required structure
# ---------------------------------------------------------------------------

class TestAuditReport:

    AUDIT_PATH = AUDIT_DIR / "phase14_6d_audit_report.md"

    def test_audit_report_exists(self) -> None:
        assert self.AUDIT_PATH.exists(), (
            f"Missing audit report: {self.AUDIT_PATH}"
        )

    def test_audit_report_minimum_size(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert len(lines) >= 100, (
            f"Audit report too short: {len(lines)} lines"
        )

    def test_audit_report_has_frontmatter(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        fm = _parse_md_frontmatter(content)
        assert fm.get("phase") == "14.6D"
        assert fm.get("operator_approved") is False
        assert fm.get("allows_implementation") is False

    def test_audit_report_has_required_sections(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        required_sections = [
            r"Files\s+Changed",
            r"Doctrines\s+Updated",
            r"Remaining\s+Blockers",
            r"Next\s+Recommended\s+Phase",
            r"Safety\s+Attestation",
        ]
        for section in required_sections:
            assert _md_has_section(content, section), (
                f"Audit report missing section matching: {section}"
            )

    def test_audit_report_lists_17_files(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        for slug in ALL_REVISED_ARTIFACTS:
            filename = f"{slug}.md" if slug in REVISED_MD_ARTIFACTS else f"{slug}.json"
            assert filename in content, (
                f"Audit report missing file reference: {filename}"
            )

    def test_audit_report_lists_15_unresolved(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        assert _md_has_text(content, r"15\s+(of\s+)?18"), (
            "Audit report missing '15 of 18' unresolved P0 count"
        )

    def test_audit_report_references_all_decisions(self) -> None:
        content = self.AUDIT_PATH.read_text(encoding="utf-8")
        for dec in DEC_REFERENCES:
            assert dec in content, (
                f"Audit report missing decision reference: {dec}"
            )


# ---------------------------------------------------------------------------
# 13. TestNoSourceCodeMutation — only canon/doc files changed
# ---------------------------------------------------------------------------

class TestNoSourceCodeMutation:
    """Verify no Python, TypeScript, or config files were modified."""

    def test_no_python_in_diff(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode != 0:
            pytest.skip("git diff failed")
        changed = result.stdout.strip().splitlines()
        py_files = [f for f in changed if f.endswith(".py") and not f.startswith("tests/")]
        assert len(py_files) == 0, (
            f"Source Python files modified (violation): {py_files}"
        )

    def test_no_typescript_in_diff(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode != 0:
            pytest.skip("git diff failed")
        changed = result.stdout.strip().splitlines()
        ts_files = [f for f in changed if f.endswith((".ts", ".tsx", ".js", ".jsx"))]
        assert len(ts_files) == 0, (
            f"Source TypeScript/JS files modified (violation): {ts_files}"
        )

    def test_no_docker_in_diff(self) -> None:
        import subprocess
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True,
            cwd=str(_REPO_ROOT),
        )
        if result.returncode != 0:
            pytest.skip("git diff failed")
        changed = result.stdout.strip().splitlines()
        docker_files = [f for f in changed if "docker" in f.lower() or "Dockerfile" in f]
        assert len(docker_files) == 0, (
            f"Docker files modified (violation): {docker_files}"
        )


# ---------------------------------------------------------------------------
# 14. TestCrossArtifactConsistency — cross-references valid
# ---------------------------------------------------------------------------

class TestCrossArtifactConsistency:

    def test_all_artifacts_reference_same_phase(self) -> None:
        for slug in REVISED_MD_ARTIFACTS:
            content = _load_md(slug)
            assert _md_has_text(content, r"14\.6B-UMH\s*\(revised\s+14\.6D\)"), (
                f"{slug} missing standardized phase reference '14.6B-UMH (revised 14.6D)'"
            )

    def test_no_artifact_claims_approved(self) -> None:
        for slug in REVISED_MD_ARTIFACTS:
            content = _load_md(slug)
            upper = content[:800].upper()
            assert "APPROVED" not in upper or "NOT APPROVED" in upper or "AWAITING" in upper or "OPERATOR_APPROVED: FALSE" in upper.replace(" ", ""), (
                f"{slug} appears to claim approval status in header"
            )

    def test_product_name_consistent(self) -> None:
        name_count = 0
        for slug in ["umh_lossless_product_canon", "umh_naming_canonicalization"]:
            content = _load_md(slug)
            name_count += _count_occurrences(content, r"Universal Meta Harness")
        assert name_count >= 3, (
            f"Product name 'Universal Meta Harness' appears only {name_count} times "
            f"across core naming artifacts (expected >= 3)"
        )


# ---------------------------------------------------------------------------
# 15. TestSpecificRevisionContent — spot checks on key revisions
# ---------------------------------------------------------------------------

class TestSpecificRevisionContent:

    def test_product_canon_reality_isomorphic(self) -> None:
        content = _load_md("umh_lossless_product_canon")
        assert _md_has_text(
            content,
            r"reality-isomorphic\s+(intelligence\s+)?harness"
        ), "Product canon missing 'reality-isomorphic intelligence harness'"

    def test_cockpit_doctrine_9_principles(self) -> None:
        content = _load_md("umh_cockpit_jarvis_doctrine")
        assert _md_has_text(content, r"\b9\b.*principle") or _md_has_text(content, r"9\."), (
            "Cockpit Jarvis doctrine should reference 9 principles"
        )

    def test_execution_boundary_safety_boundaries(self) -> None:
        content = _load_md("umh_execution_boundary_model")
        assert _md_has_section(content, r"safety\s+boundar"), (
            "Execution boundary model missing Safety Boundaries section"
        )

    def test_governance_mutation_risk_classes(self) -> None:
        content = _load_md("umh_governance_approval_lifecycle")
        for risk in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            assert risk in content, (
                f"Governance lifecycle missing risk class: {risk}"
            )

    def test_naming_canon_rule_8_and_9(self) -> None:
        content = _load_md("umh_naming_canonicalization")
        assert _md_has_text(content, r"8\.\s+\*\*Do not rename"), (
            "Naming canon missing Rule 8 (do not rename to engine)"
        )
        assert _md_has_text(content, r"9\.\s+\*\*"), (
            "Naming canon missing Rule 9"
        )

    def test_json_panel_inventory_has_stage1_context(self) -> None:
        data = _load_json("umh_cockpit_screen_panel_inventory")
        assert "stage1_context" in data, (
            "Panel inventory JSON missing stage1_context field"
        )

    def test_json_panel_inventory_has_reality_model_note(self) -> None:
        data = _load_json("umh_cockpit_screen_panel_inventory")
        assert "reality_model_mapping_note" in data, (
            "Panel inventory JSON missing reality_model_mapping_note field"
        )

    def test_world_model_renamed_to_reality_model(self) -> None:
        content = _load_md("umh_world_model_memory_architecture")
        assert _md_has_section(content, r"reality\s+model"), (
            "World model architecture missing Reality Model section heading"
        )

    def test_signal_canon_has_12_layer(self) -> None:
        content = _load_md("umh_signal_interpretation_decomposition_canon")
        assert _md_has_text(content, r"12[- ]layer"), (
            "Signal canon missing 12-layer reference"
        )

    def test_substrate_canon_reality_model_infrastructure(self) -> None:
        content = _load_md("umh_code_resolved_substrate_canon")
        assert _md_has_text(content, r"reality[- ]?model\s+infrastructure"), (
            "Substrate canon missing 'reality-model infrastructure'"
        )
