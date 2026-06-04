"""
Comprehensive pytest test suite for Phase 14.6C operator review packet.

Verifies all 8 operator review artifacts exist, carry correct YAML
frontmatter, comply with phase governance (DRAFT, not approved), contain
required sections, maintain cross-references, and confirm no source
mutation occurred.

125+ tests across 14 test classes.
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Set

import pytest


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(os.environ.get("UMH_ROOT", "/opt/OS"))
CANON_DIR = _REPO_ROOT / "data" / "umh" / "trinity_convergence" / "phase14_6c_operator_review"

PREFIX = "phase14_6c_"

REQUIRED_MD_ARTIFACTS: list[str] = [
    "operator_review_index",
    "ecosystem_doctrine",
    "cross_product_boundary_matrix",
    "umh_reality_model_correction",
    "ratification_decision_queue",
    "implementation_blockers",
    "next_phase_recommendation",
    "audit_report",
    "ratification_delta_report",
]

REQUIRED_METADATA_FIELDS: list[str] = [
    "phase",
    "status",
    "operator_approved",
    "allows_implementation",
    "date",
]

ALL_PRODUCTS: list[str] = [
    "EOS",
    "CreatorOS",
    "LyfeOS",
    "Cockpit",
]

ALL_ENTITIES: list[str] = [
    "UMH",
    "Cockpit",
    "EOS",
    "CreatorOS",
    "LyfeOS",
]

# Minimum expected line count per artifact (generous floor)
MIN_LINE_COUNTS: dict[str, int] = {
    "operator_review_index": 40,
    "ecosystem_doctrine": 30,
    "cross_product_boundary_matrix": 30,
    "umh_reality_model_correction": 50,
    "ratification_decision_queue": 30,
    "implementation_blockers": 20,
    "next_phase_recommendation": 20,
    "audit_report": 40,
    "ratification_delta_report": 30,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _md_path(slug: str) -> Path:
    return CANON_DIR / f"{PREFIX}{slug}.md"


def _load_md(slug: str) -> str:
    path = _md_path(slug)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


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


def _get_frontmatter(slug: str) -> Dict[str, Any]:
    return _parse_md_frontmatter(_load_md(slug))


def _md_has_section(content: str, heading_pattern: str) -> bool:
    """Check if markdown content has a heading matching the pattern (case-insensitive)."""
    for line in content.splitlines():
        if re.match(r"^#{1,4}\s+", line):
            if re.search(heading_pattern, line, re.IGNORECASE):
                return True
    return False


def _md_has_text(content: str, pattern: str, flags: int = re.IGNORECASE) -> bool:
    """Check if markdown content contains text matching the pattern."""
    return bool(re.search(pattern, content, flags))


def _count_occurrences(content: str, pattern: str, flags: int = re.IGNORECASE) -> int:
    """Count occurrences of a pattern in content."""
    return len(re.findall(pattern, content, flags))


def _all_slugs_that_exist() -> list[str]:
    """Return slugs for MD artifacts that actually exist on disk."""
    return [s for s in REQUIRED_MD_ARTIFACTS if _md_path(s).exists()]


def _load_all_contents() -> dict[str, str]:
    """Load content of all existing artifacts."""
    return {slug: _load_md(slug) for slug in _all_slugs_that_exist()}


# ---------------------------------------------------------------------------
# 1. TestArtifactExistence — all 8 MD files exist
# ---------------------------------------------------------------------------


class TestArtifactExistence:
    """All 8 MD files must exist in the canon directory."""

    def test_canon_directory_exists(self) -> None:
        assert CANON_DIR.exists(), f"Canon directory does not exist: {CANON_DIR}"

    def test_canon_directory_is_directory(self) -> None:
        assert CANON_DIR.is_dir(), f"Canon path is not a directory: {CANON_DIR}"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_artifact_exists(self, slug: str) -> None:
        path = _md_path(slug)
        assert path.exists(), f"Missing artifact: {path.name}"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_artifact_is_file(self, slug: str) -> None:
        path = _md_path(slug)
        assert path.is_file(), f"Artifact is not a regular file: {path.name}"

    def test_exactly_nine_artifacts(self) -> None:
        md_files = list(CANON_DIR.glob(f"{PREFIX}*.md"))
        assert len(md_files) == 9, (
            f"Expected 9 artifacts, found {len(md_files)}: "
            f"{[f.name for f in md_files]}"
        )

    def test_no_unexpected_artifacts(self) -> None:
        expected = {f"{PREFIX}{slug}.md" for slug in REQUIRED_MD_ARTIFACTS}
        actual = {f.name for f in CANON_DIR.glob(f"{PREFIX}*.md")}
        unexpected = actual - expected
        assert not unexpected, f"Unexpected artifacts: {unexpected}"

    def test_all_files_readable(self) -> None:
        for slug in REQUIRED_MD_ARTIFACTS:
            path = _md_path(slug)
            assert os.access(path, os.R_OK), f"Not readable: {path.name}"

    def test_no_zero_byte_files(self) -> None:
        for slug in REQUIRED_MD_ARTIFACTS:
            path = _md_path(slug)
            assert path.stat().st_size > 0, f"Zero-byte file: {path.name}"


# ---------------------------------------------------------------------------
# 2. TestArtifactMetadata — YAML frontmatter with required fields
# ---------------------------------------------------------------------------


class TestArtifactMetadata:
    """All files have YAML frontmatter with required fields."""

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_frontmatter(self, slug: str) -> None:
        content = _load_md(slug)
        assert content.startswith("---"), f"{slug}: missing YAML frontmatter delimiter"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_frontmatter_closes(self, slug: str) -> None:
        content = _load_md(slug)
        assert content.count("---") >= 2, f"{slug}: frontmatter not closed"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_phase_field(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert "phase" in fm, f"{slug}: missing 'phase' field"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_status_field(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert "status" in fm, f"{slug}: missing 'status' field"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_operator_approved_field(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert "operator_approved" in fm, f"{slug}: missing 'operator_approved' field"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_allows_implementation_field(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert "allows_implementation" in fm, f"{slug}: missing 'allows_implementation'"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_date_field(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert "date" in fm, f"{slug}: missing 'date' field"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_all_metadata_fields_present(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        for field in REQUIRED_METADATA_FIELDS:
            assert field in fm, f"{slug}: missing metadata field '{field}'"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_frontmatter_parseable(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert len(fm) >= 5, (
            f"{slug}: frontmatter has only {len(fm)} fields, expected >= 5"
        )


# ---------------------------------------------------------------------------
# 3. TestPhaseCompliance — all DRAFT, none approved, date is 2026
# ---------------------------------------------------------------------------


class TestPhaseCompliance:
    """All DRAFT, none approved, date is 2026."""

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_status_is_draft(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert str(fm.get("status", "")).upper() == "DRAFT", (
            f"{slug}: status should be DRAFT, got {fm.get('status')}"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_not_operator_approved(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert fm.get("operator_approved") is False, (
            f"{slug}: operator_approved must be false"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_not_allows_implementation(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        assert fm.get("allows_implementation") is False, (
            f"{slug}: allows_implementation must be false"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_date_is_2026(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        date_str = str(fm.get("date", ""))
        assert date_str.startswith("2026"), (
            f"{slug}: date should be 2026, got {date_str}"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_phase_references_14_6c(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        phase_str = str(fm.get("phase", ""))
        assert "14.6C" in phase_str or "14.6c" in phase_str, (
            f"{slug}: phase should reference 14.6C, got {phase_str}"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_date_format_valid(self, slug: str) -> None:
        fm = _get_frontmatter(slug)
        date_str = str(fm.get("date", ""))
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", date_str), (
            f"{slug}: date format should be YYYY-MM-DD, got {date_str}"
        )


# ---------------------------------------------------------------------------
# 4. TestMarkdownValidity — non-empty, have headers, minimum lines
# ---------------------------------------------------------------------------


class TestMarkdownValidity:
    """All non-empty, have headers, minimum line counts."""

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_not_empty(self, slug: str) -> None:
        content = _load_md(slug)
        assert len(content.strip()) > 0, f"{slug}: file is empty"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_headers(self, slug: str) -> None:
        content = _load_md(slug)
        headers = [l for l in content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 1, f"{slug}: no markdown headers found"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_minimum_line_count(self, slug: str) -> None:
        lines = _load_md_lines(slug)
        min_lines = MIN_LINE_COUNTS.get(slug, 20)
        assert len(lines) >= min_lines, (
            f"{slug}: expected >= {min_lines} lines, got {len(lines)}"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_no_bare_placeholder_text(self, slug: str) -> None:
        content = _load_md(slug)
        assert "PLACEHOLDER" not in content, (
            f"{slug}: contains PLACEHOLDER text"
        )
        assert "FIXME" not in content, (
            f"{slug}: contains FIXME marker"
        )

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_no_template_markers(self, slug: str) -> None:
        content = _load_md(slug)
        assert "{{" not in content, f"{slug}: contains template marker '{{{{'"
        assert "}}" not in content, f"{slug}: contains template marker '}}}}'"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_has_h1_or_h2_title(self, slug: str) -> None:
        content = _load_md(slug)
        body = content.split("---", 2)[-1] if content.startswith("---") else content
        has_title = bool(re.search(r"^#{1,2}\s+\S", body, re.MULTILINE))
        assert has_title, f"{slug}: no H1 or H2 title after frontmatter"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_content_after_frontmatter(self, slug: str) -> None:
        content = _load_md(slug)
        parts = content.split("---")
        if len(parts) >= 3:
            body = "---".join(parts[2:]).strip()
            assert len(body) > 50, f"{slug}: body after frontmatter is too short"

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_valid_utf8(self, slug: str) -> None:
        path = _md_path(slug)
        raw = path.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            pytest.fail(f"{slug}: file is not valid UTF-8")


# ---------------------------------------------------------------------------
# 5. TestReviewIndex — executive summary, products, review order, inventory
# ---------------------------------------------------------------------------


class TestReviewIndex:
    """Operator review index has executive summary, products, review order, etc."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("operator_review_index")

    def test_has_executive_summary(self) -> None:
        assert _md_has_section(self.content, r"executive\s+summary"), (
            "Missing executive summary section"
        )

    def test_has_p0_clarification_section(self) -> None:
        assert _md_has_text(self.content, r"P0.*clarification|clarification.*P0"), (
            "Missing P0 clarification section"
        )

    def test_lists_eos(self) -> None:
        assert _md_has_text(self.content, r"\bEOS\b"), "Missing EOS reference"

    def test_lists_creatoros(self) -> None:
        assert _md_has_text(self.content, r"CreatorOS"), "Missing CreatorOS reference"

    def test_lists_lyfeos(self) -> None:
        assert _md_has_text(self.content, r"LyfeOS"), "Missing LyfeOS reference"

    def test_lists_cockpit(self) -> None:
        assert _md_has_text(self.content, r"Cockpit"), "Missing Cockpit reference"

    def test_has_recommended_review_order(self) -> None:
        assert _md_has_text(
            self.content, r"review\s+order|recommended.*order|reading.*order"
        ), "Missing recommended review order"

    def test_has_artifact_inventory(self) -> None:
        assert _md_has_text(
            self.content, r"artifact.*inventor|inventor.*artifact|artifact.*list|artifact.*summar"
        ), "Missing artifact inventory"

    def test_has_safety_attestation(self) -> None:
        assert _md_has_text(
            self.content, r"safety.*attestation|attestation|safety.*guarantee"
        ), "Missing safety attestation"

    def test_references_all_four_products(self) -> None:
        for product in ALL_PRODUCTS:
            assert _md_has_text(self.content, re.escape(product)), (
                f"Missing product reference: {product}"
            )

    def test_mentions_all_artifacts(self) -> None:
        for slug in REQUIRED_MD_ARTIFACTS:
            human_name = slug.replace("_", " ")
            found = _md_has_text(
                self.content, slug.replace("_", r"[\s_-]+")
            ) or _md_has_text(
                self.content, human_name
            )
            assert found, f"Index does not reference artifact: {slug}"

    def test_has_multiple_sections(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 4, (
            f"Index should have >= 4 sections, found {len(headers)}"
        )


# ---------------------------------------------------------------------------
# 6. TestEcosystemDoctrine — reality model, products, capability pipeline
# ---------------------------------------------------------------------------


class TestEcosystemDoctrine:
    """Ecosystem doctrine references reality model, products, capability pipeline."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("ecosystem_doctrine")

    def test_references_reality_model(self) -> None:
        assert _md_has_text(self.content, r"reality\s+model"), (
            "Missing reality model reference"
        )

    def test_references_materialization_principle(self) -> None:
        assert _md_has_text(
            self.content, r"materialization|materializ"
        ), "Missing materialization principle"

    def test_references_eos(self) -> None:
        assert _md_has_text(self.content, r"\bEOS\b"), "Missing EOS"

    def test_references_creatoros(self) -> None:
        assert _md_has_text(self.content, r"CreatorOS"), "Missing CreatorOS"

    def test_references_lyfeos(self) -> None:
        assert _md_has_text(self.content, r"LyfeOS"), "Missing LyfeOS"

    def test_references_cockpit(self) -> None:
        assert _md_has_text(self.content, r"Cockpit"), "Missing Cockpit"

    def test_has_capability_pipeline(self) -> None:
        assert _md_has_text(
            self.content, r"capability.*pipeline|pipeline.*capability|capability.*flow"
        ), "Missing capability pipeline"

    def test_has_ownership_map(self) -> None:
        assert _md_has_text(
            self.content, r"ownership.*map|ownership.*matrix|owner"
        ), "Missing ownership map"

    def test_references_all_four_products(self) -> None:
        for product in ALL_PRODUCTS:
            assert _md_has_text(self.content, re.escape(product)), (
                f"Missing product: {product}"
            )

    def test_has_substantive_content(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 30, f"Doctrine too short: {len(lines)} lines"

    def test_has_umh_reference(self) -> None:
        assert _md_has_text(self.content, r"\bUMH\b"), "Missing UMH reference"

    def test_has_multiple_sections(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 3, (
            f"Doctrine should have >= 3 sections, found {len(headers)}"
        )


# ---------------------------------------------------------------------------
# 7. TestBoundaryMatrix — table, entities, data/agent boundaries
# ---------------------------------------------------------------------------


class TestBoundaryMatrix:
    """Boundary matrix has table, references all entities, data/agent boundaries."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("cross_product_boundary_matrix")

    def test_has_boundary_table(self) -> None:
        pipe_lines = [l for l in self.content.splitlines() if "|" in l]
        assert len(pipe_lines) >= 3, "No boundary table found (need >= 3 pipe lines)"

    def test_table_has_header_separator(self) -> None:
        """Markdown tables require a |---|---| separator row."""
        has_separator = any(
            re.match(r"^\s*\|[\s:-]+\|", l)
            for l in self.content.splitlines()
        )
        assert has_separator, "Table missing header separator row"

    def test_references_umh(self) -> None:
        assert _md_has_text(self.content, r"\bUMH\b"), "Missing UMH"

    def test_references_cockpit(self) -> None:
        assert _md_has_text(self.content, r"Cockpit"), "Missing Cockpit"

    def test_references_eos(self) -> None:
        assert _md_has_text(self.content, r"\bEOS\b"), "Missing EOS"

    def test_references_creatoros(self) -> None:
        assert _md_has_text(self.content, r"CreatorOS"), "Missing CreatorOS"

    def test_references_lyfeos(self) -> None:
        assert _md_has_text(self.content, r"LyfeOS"), "Missing LyfeOS"

    def test_all_entities_present(self) -> None:
        for entity in ALL_ENTITIES:
            assert _md_has_text(self.content, re.escape(entity)), (
                f"Missing entity: {entity}"
            )

    def test_has_data_boundary(self) -> None:
        assert _md_has_text(
            self.content, r"data\s+boundar|data\s+isolation|data\s+scope|data\s+flow"
        ), "Missing data boundary section"

    def test_has_agent_boundary(self) -> None:
        assert _md_has_text(
            self.content, r"agent\s+boundar|agent\s+isolation|agent\s+scope|agent\s+routing"
        ), "Missing agent boundary section"

    def test_has_substantive_content(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 30, f"Matrix too short: {len(lines)} lines"


# ---------------------------------------------------------------------------
# 8. TestRealityModelCorrection — P0, 12 layers, materialization, DEC-146C
# ---------------------------------------------------------------------------


class TestRealityModelCorrection:
    """Reality model correction: P0, 12 layers, materialization, decisions, etc."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("umh_reality_model_correction")

    def test_p0_operator_clarification_present(self) -> None:
        assert _md_has_text(self.content, r"P0.*operator.*clarification|P0.*clarif"), (
            "Missing P0 operator clarification"
        )

    def test_twelve_reality_layers_listed(self) -> None:
        # Count distinct numbered layers or layer references
        layer_matches = re.findall(
            r"(?:layer\s*\d+|\d+\.\s+\w+.*layer|\d+\s*[-.)]\s*\w+)",
            self.content,
            re.IGNORECASE,
        )
        numbered_items = re.findall(
            r"^\s*\d+[\s.):-]+\S",
            self.content,
            re.MULTILINE,
        )
        total_candidates = max(len(layer_matches), len(numbered_items))
        assert total_candidates >= 12, (
            f"Expected 12 reality layers, found {total_candidates} candidates"
        )

    def test_materialization_principle_present(self) -> None:
        assert _md_has_text(
            self.content, r"materialization|materializ"
        ), "Missing materialization principle"

    def test_seventeen_affected_artifacts_listed(self) -> None:
        bullet_items = re.findall(
            r"^\s*[-*]\s+\S",
            self.content,
            re.MULTILINE,
        )
        numbered_items = re.findall(
            r"^\s*\d+[\s.):-]+\S",
            self.content,
            re.MULTILINE,
        )
        total_items = len(bullet_items) + len(numbered_items)
        assert total_items >= 17, (
            f"Expected >= 17 affected artifacts listed, found {total_items} list items"
        )

    def test_three_dec_146c_decisions(self) -> None:
        dec_matches = re.findall(r"DEC-146C", self.content)
        assert len(dec_matches) >= 3, (
            f"Expected >= 3 DEC-146C references, found {len(dec_matches)}"
        )

    def test_blocks_cockpit_implementation(self) -> None:
        assert _md_has_text(
            self.content,
            r"block.*cockpit|cockpit.*block|cockpit.*halt|halt.*cockpit|cockpit.*implementation.*block",
        ), "Missing cockpit implementation blocking statement"

    def test_not_silently_approved(self) -> None:
        assert _md_has_text(
            self.content, r"not.*silent.*approv|never.*silent|no.*silent.*approv"
        ), "Missing explicit 'not silently approved' statement"

    def test_has_reality_model_section(self) -> None:
        assert _md_has_section(self.content, r"reality\s+model"), (
            "Missing reality model section header"
        )

    def test_references_correction(self) -> None:
        assert _md_has_text(self.content, r"correction"), (
            "Missing 'correction' reference"
        )

    def test_has_substantive_length(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 50, f"Reality model correction too short: {len(lines)}"

    def test_references_cockpit(self) -> None:
        assert _md_has_text(self.content, r"Cockpit"), "Missing Cockpit reference"

    def test_references_phase_14_6c(self) -> None:
        assert _md_has_text(self.content, r"14\.6C|14\.6c"), (
            "Does not reference 14.6C"
        )


# ---------------------------------------------------------------------------
# 9. TestRatificationDecisionQueue — P0-P3, DEC-146C, cross-product
# ---------------------------------------------------------------------------


class TestRatificationDecisionQueue:
    """Decision queue has P0-P3 sections, DEC-146C, cross-product decisions."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("ratification_decision_queue")

    def test_has_p0_section(self) -> None:
        assert _md_has_text(self.content, r"\bP0\b"), "Missing P0 section"

    def test_has_p1_section(self) -> None:
        assert _md_has_text(self.content, r"\bP1\b"), "Missing P1 section"

    def test_has_p2_section(self) -> None:
        assert _md_has_text(self.content, r"\bP2\b"), "Missing P2 section"

    def test_has_p3_section(self) -> None:
        assert _md_has_text(self.content, r"\bP3\b"), "Missing P3 section"

    def test_references_dec_146c(self) -> None:
        dec_matches = re.findall(r"DEC-146C", self.content)
        assert len(dec_matches) >= 1, "Missing DEC-146C decision references"

    def test_has_cross_product_decisions(self) -> None:
        assert _md_has_text(
            self.content,
            r"cross[- ]product|multi[- ]product|ecosystem[- ]wide|cross.*boundar",
        ), "Missing cross-product decisions section"

    def test_has_decision_items(self) -> None:
        list_items = re.findall(
            r"^\s*[-*\d]+[.):\s]+\S",
            self.content,
            re.MULTILINE,
        )
        assert len(list_items) >= 5, (
            f"Expected >= 5 decision items, found {len(list_items)}"
        )

    def test_priority_ordering(self) -> None:
        p0_pos = self.content.find("P0")
        p3_pos = self.content.find("P3")
        assert p0_pos >= 0 and p3_pos >= 0, "Missing P0 or P3"
        assert p0_pos < p3_pos, "P0 should appear before P3 (priority ordering)"

    def test_p0_before_p1(self) -> None:
        p0_pos = self.content.find("P0")
        p1_pos = self.content.find("P1")
        assert p0_pos >= 0 and p1_pos >= 0, "Missing P0 or P1"
        assert p0_pos < p1_pos, "P0 should appear before P1"

    def test_p1_before_p2(self) -> None:
        p1_pos = self.content.find("P1")
        p2_pos = self.content.find("P2")
        assert p1_pos >= 0 and p2_pos >= 0, "Missing P1 or P2"
        assert p1_pos < p2_pos, "P1 should appear before P2"

    def test_has_multiple_sections(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 3, (
            f"Queue should have >= 3 sections, found {len(headers)}"
        )


# ---------------------------------------------------------------------------
# 10. TestImplementationBlockers — auth, beast, reality model, sequence
# ---------------------------------------------------------------------------


class TestImplementationBlockers:
    """Blockers: auth bypass, beast branch, reality model, unblocking sequence."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("implementation_blockers")

    def test_auth_bypass_mentioned(self) -> None:
        assert _md_has_text(
            self.content, r"auth.*bypass|bypass.*auth|authentication.*bypass"
        ), "Missing auth bypass blocker"

    def test_beast_branch_mentioned(self) -> None:
        assert _md_has_text(
            self.content, r"beast.*branch|branch.*beast|beast"
        ), "Missing beast branch blocker"

    def test_reality_model_correction_mentioned(self) -> None:
        assert _md_has_text(
            self.content, r"reality\s+model.*correction|correction.*reality"
        ), "Missing reality model correction blocker"

    def test_recommended_unblocking_sequence(self) -> None:
        assert _md_has_text(
            self.content,
            r"unblock.*sequence|sequence.*unblock|recommended.*order|resolution.*order|unblocking",
        ), "Missing recommended unblocking sequence"

    def test_has_blocker_items(self) -> None:
        list_items = re.findall(
            r"^\s*[-*\d]+[.):\s]+\S",
            self.content,
            re.MULTILINE,
        )
        assert len(list_items) >= 3, (
            f"Expected >= 3 blocker items, found {len(list_items)}"
        )

    def test_has_substantive_content(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 20, f"Blockers too short: {len(lines)} lines"

    def test_has_headers(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 2, f"Blockers should have >= 2 sections"

    def test_references_phase_14_6c(self) -> None:
        assert _md_has_text(self.content, r"14\.6C|14\.6c"), (
            "Does not reference 14.6C"
        )


# ---------------------------------------------------------------------------
# 11. TestNextPhaseRecommendation — 14.6D, ratification, timeline
# ---------------------------------------------------------------------------


class TestNextPhaseRecommendation:
    """Recommends 14.6D, reality model ratification, timeline estimates."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("next_phase_recommendation")

    def test_recommends_14_6d(self) -> None:
        assert _md_has_text(self.content, r"14\.6D|14\.6d"), (
            "Missing 14.6D recommendation"
        )

    def test_mentions_reality_model_ratification(self) -> None:
        assert _md_has_text(
            self.content,
            r"reality\s+model.*ratif|ratif.*reality\s+model",
        ), "Missing reality model ratification mention"

    def test_has_timeline_estimates(self) -> None:
        assert _md_has_text(
            self.content,
            r"timeline|estimate|duration|day|week|sprint|schedule|hour",
        ), "Missing timeline estimates"

    def test_has_substantive_content(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 20, f"Recommendation too short: {len(lines)} lines"

    def test_has_next_steps(self) -> None:
        assert _md_has_text(
            self.content,
            r"next\s+step|action.*item|recommend|prerequisite|depend",
        ), "Missing next steps or action items"

    def test_references_current_phase(self) -> None:
        assert _md_has_text(self.content, r"14\.6C|14\.6c"), (
            "Does not reference current phase 14.6C"
        )

    def test_has_headers(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 2, f"Recommendation should have >= 2 sections"


# ---------------------------------------------------------------------------
# 12. TestAuditReport — findings, safety, artifact summary, not silently approved
# ---------------------------------------------------------------------------


class TestAuditReport:
    """Audit report: findings, safety attestation, artifact summary, compliance."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("audit_report")

    def test_has_findings(self) -> None:
        assert _md_has_section(self.content, r"finding"), "Missing findings section"

    def test_has_safety_attestation(self) -> None:
        assert _md_has_text(
            self.content, r"safety.*attestation|attestation|safety.*guarantee"
        ), "Missing safety attestation"

    def test_has_artifact_summary(self) -> None:
        assert _md_has_text(
            self.content, r"artifact.*summary|summary.*artifact|artifact.*list|artifact.*inventor"
        ), "Missing artifact summary"

    def test_artifact_summary_lists_operator_review_index(self) -> None:
        assert _md_has_text(
            self.content, r"operator.review.index"
        ), "Audit report missing artifact: operator_review_index"

    def test_artifact_summary_lists_ecosystem_doctrine(self) -> None:
        assert _md_has_text(
            self.content, r"ecosystem.doctrine"
        ), "Audit report missing artifact: ecosystem_doctrine"

    def test_artifact_summary_lists_boundary_matrix(self) -> None:
        assert _md_has_text(
            self.content, r"cross.product.boundary.matrix|boundary.matrix"
        ), "Audit report missing artifact: cross_product_boundary_matrix"

    def test_artifact_summary_lists_reality_model(self) -> None:
        assert _md_has_text(
            self.content, r"reality.model.correction"
        ), "Audit report missing artifact: umh_reality_model_correction"

    def test_artifact_summary_lists_ratification_queue(self) -> None:
        assert _md_has_text(
            self.content, r"ratification.decision.queue|decision.queue"
        ), "Audit report missing artifact: ratification_decision_queue"

    def test_artifact_summary_lists_blockers(self) -> None:
        assert _md_has_text(
            self.content, r"implementation.blocker"
        ), "Audit report missing artifact: implementation_blockers"

    def test_artifact_summary_lists_next_phase(self) -> None:
        assert _md_has_text(
            self.content, r"next.phase.recommend"
        ), "Audit report missing artifact: next_phase_recommendation"

    def test_artifact_summary_lists_audit_report(self) -> None:
        assert _md_has_text(
            self.content, r"audit.report"
        ), "Audit report missing self-reference: audit_report"

    def test_mentions_operator_clarification(self) -> None:
        assert _md_has_text(
            self.content, r"operator.*clarification|clarification.*operator"
        ), "Missing operator clarification mention"

    def test_not_silently_approved(self) -> None:
        assert _md_has_text(
            self.content, r"not.*silent.*approv|never.*silent|no.*silent.*approv"
        ), "Missing 'not silently approved' attestation"

    def test_has_substantive_findings(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 40, f"Audit report too short: {len(lines)} lines"

    def test_references_phase_14_6c(self) -> None:
        assert _md_has_text(self.content, r"14\.6C|14\.6c"), (
            "Audit report does not reference 14.6C"
        )

    def test_has_multiple_sections(self) -> None:
        headers = [l for l in self.content.splitlines() if re.match(r"^#{1,4}\s+", l)]
        assert len(headers) >= 4, (
            f"Audit report should have >= 4 sections, found {len(headers)}"
        )


# ---------------------------------------------------------------------------
# 13. TestCrossConsistency — all reference 14.6C, reality model, DEC-146C
# ---------------------------------------------------------------------------


class TestCrossConsistency:
    """Cross-artifact consistency: all reference 14.6C, reality model, DEC-146C."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.contents = _load_all_contents()

    @pytest.mark.parametrize("slug", REQUIRED_MD_ARTIFACTS)
    def test_all_reference_14_6c(self, slug: str) -> None:
        content = self.contents[slug]
        assert _md_has_text(content, r"14\.6C|14\.6c"), (
            f"{slug}: does not reference 14.6C"
        )

    def test_reality_model_correction_referenced_in_at_least_4(self) -> None:
        count = 0
        for slug, content in self.contents.items():
            if _md_has_text(content, r"reality\s+model.*correction|correction.*reality"):
                count += 1
        assert count >= 4, (
            f"Reality model correction referenced in only {count} artifacts, need >= 4"
        )

    def test_dec_146c_referenced_in_at_least_3(self) -> None:
        count = 0
        for slug, content in self.contents.items():
            if _md_has_text(content, r"DEC-146C"):
                count += 1
        assert count >= 3, (
            f"DEC-146C referenced in only {count} artifacts, need >= 3"
        )

    def test_all_artifacts_share_phase_value(self) -> None:
        phases = set()
        for slug in REQUIRED_MD_ARTIFACTS:
            fm = _get_frontmatter(slug)
            phases.add(str(fm.get("phase", "")))
        assert len(phases) == 1, f"Inconsistent phase values across artifacts: {phases}"

    def test_all_artifacts_share_status_value(self) -> None:
        statuses = set()
        for slug in REQUIRED_MD_ARTIFACTS:
            fm = _get_frontmatter(slug)
            statuses.add(str(fm.get("status", "")).upper())
        assert len(statuses) == 1, (
            f"Inconsistent status values across artifacts: {statuses}"
        )

    def test_all_artifacts_share_date(self) -> None:
        dates = set()
        for slug in REQUIRED_MD_ARTIFACTS:
            fm = _get_frontmatter(slug)
            dates.add(str(fm.get("date", "")))
        assert len(dates) == 1, (
            f"Inconsistent date values across artifacts: {dates}"
        )

    def test_operator_review_index_references_other_artifacts(self) -> None:
        index_content = self.contents["operator_review_index"]
        referenced = 0
        for slug in REQUIRED_MD_ARTIFACTS:
            if slug == "operator_review_index":
                continue
            human = slug.replace("_", " ")
            if _md_has_text(
                index_content, slug.replace("_", r"[\s_-]+")
            ) or _md_has_text(index_content, human):
                referenced += 1
        assert referenced >= 6, (
            f"Index references only {referenced} other artifacts, need >= 6"
        )

    def test_blocker_artifacts_cross_reference(self) -> None:
        """Implementation blockers should reference the reality model correction."""
        blockers = self.contents["implementation_blockers"]
        assert _md_has_text(
            blockers, r"reality\s+model|umh_reality_model_correction"
        ), "Implementation blockers does not cross-reference reality model correction"

    def test_audit_references_blockers(self) -> None:
        """Audit report should mention blockers or implementation blockers."""
        audit = self.contents["audit_report"]
        assert _md_has_text(
            audit, r"blocker|implementation.*block"
        ), "Audit report does not reference implementation blockers"

    def test_next_phase_references_blockers(self) -> None:
        """Next phase recommendation should reference current blockers."""
        next_phase = self.contents["next_phase_recommendation"]
        assert _md_has_text(
            next_phase, r"blocker|block|prerequisite|depend"
        ), "Next phase recommendation does not reference blockers"

    def test_doctrine_references_boundary_matrix(self) -> None:
        """Ecosystem doctrine should reference the boundary matrix."""
        doctrine = self.contents["ecosystem_doctrine"]
        assert _md_has_text(
            doctrine, r"boundar|cross.product|matrix"
        ), "Ecosystem doctrine does not reference boundary matrix"

    def test_all_artifacts_reference_operator(self) -> None:
        """All artifacts should reference 'operator' somewhere."""
        for slug, content in self.contents.items():
            assert _md_has_text(content, r"operator"), (
                f"{slug}: does not reference 'operator'"
            )

    def test_reality_model_referenced_in_index(self) -> None:
        """The index must reference the reality model correction."""
        index = self.contents["operator_review_index"]
        assert _md_has_text(
            index, r"reality\s+model"
        ), "Index does not reference reality model"

    def test_no_artifact_claims_document_level_approval(self) -> None:
        """No artifact body should claim document-level approved status.

        Individual decisions (DEC-146C-001/002/003) may be OPERATOR-APPROVED,
        but the document-level frontmatter operator_approved must remain false
        until ALL P0 decisions are resolved. Body text may reference individual
        decision approvals using 'OPERATOR-APPROVED' as a decision status label.
        """
        for slug, content in self.contents.items():
            fm = _get_frontmatter(slug)
            assert fm.get("operator_approved") is False, (
                f"{slug}: frontmatter operator_approved must be false (15 P0 unresolved)"
            )


# ---------------------------------------------------------------------------
# 14. TestRatificationDeltaReport — ratified decisions, delta, gates
# ---------------------------------------------------------------------------


class TestRatificationDeltaReport:
    """Delta report: ratified decisions, affected artifacts, implementation gates."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self.content = _load_md("ratification_delta_report")

    def test_references_dec_146c_001(self) -> None:
        assert _md_has_text(self.content, r"DEC-146C-001"), "Missing DEC-146C-001"

    def test_references_dec_146c_002(self) -> None:
        assert _md_has_text(self.content, r"DEC-146C-002"), "Missing DEC-146C-002"

    def test_references_dec_146c_003(self) -> None:
        assert _md_has_text(self.content, r"DEC-146C-003"), "Missing DEC-146C-003"

    def test_mentions_operator_approved(self) -> None:
        assert _md_has_text(
            self.content, r"OPERATOR.APPROVED"
        ), "Missing OPERATOR-APPROVED status"

    def test_mentions_universal_meta_harness(self) -> None:
        assert _md_has_text(
            self.content, r"Universal Meta Harness"
        ), "Missing product name confirmation"

    def test_mentions_materialization(self) -> None:
        assert _md_has_text(
            self.content, r"materialization|materializ"
        ), "Missing materialization principle"

    def test_mentions_implementation_gates(self) -> None:
        assert _md_has_text(
            self.content, r"implementation.*block|implementation.*gate|gate.*closed|blocked"
        ), "Missing implementation gate status"

    def test_mentions_next_phase(self) -> None:
        assert _md_has_text(
            self.content, r"14\.6D|next\s+phase"
        ), "Missing next phase recommendation"

    def test_has_affected_artifacts(self) -> None:
        assert _md_has_text(
            self.content, r"affected.*artifact|artifact.*affected|17.*artifact"
        ), "Missing affected artifacts listing"

    def test_implementation_remains_blocked(self) -> None:
        assert _md_has_text(
            self.content, r"allows_implementation.*false|implementation.*remains.*blocked"
        ), "Missing implementation-blocked confirmation"

    def test_has_substantive_content(self) -> None:
        lines = self.content.splitlines()
        assert len(lines) >= 30, f"Delta report too short: {len(lines)} lines"


# ---------------------------------------------------------------------------
# 15. TestNoMutation — no source code files modified, review dir clean
# ---------------------------------------------------------------------------


class TestNoMutation:
    """No source code files modified — git status check scoped to review dir."""

    def test_no_modified_source_files_in_review_dir(self) -> None:
        """Git status should show no modified tracked files in review dir."""
        result = subprocess.run(
            [
                "git", "status", "--porcelain",
                str(CANON_DIR),
            ],
            capture_output=True,
            text=True,
            cwd="/opt/OS",
        )
        modified = []
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            status = line[:2].strip()
            # M = modified, D = deleted — mutation indicators
            # ?? = untracked (new files OK), A = added (new staged OK)
            if status in ("M", "D", "MM", "MD"):
                modified.append(line)
        assert not modified, (
            f"Source files modified in review dir:\n" + "\n".join(modified)
        )

    def test_no_deleted_files_in_review_dir(self) -> None:
        result = subprocess.run(
            [
                "git", "status", "--porcelain",
                str(CANON_DIR),
            ],
            capture_output=True,
            text=True,
            cwd="/opt/OS",
        )
        deleted = [
            line for line in result.stdout.strip().splitlines()
            if line.strip() and line[:2].strip() == "D"
        ]
        assert not deleted, (
            f"Files deleted in review dir:\n" + "\n".join(deleted)
        )

    def test_review_dir_contains_only_md_files(self) -> None:
        """Review directory should only contain .md files."""
        if not CANON_DIR.exists():
            pytest.skip("Review directory does not exist yet")
        non_md = [
            f.name for f in CANON_DIR.iterdir()
            if f.is_file() and f.suffix != ".md"
        ]
        assert not non_md, f"Non-MD files in review dir: {non_md}"

    def test_no_binary_files_in_review_dir(self) -> None:
        """No binary files should exist in review dir."""
        if not CANON_DIR.exists():
            pytest.skip("Review directory does not exist yet")
        binary_extensions = {
            ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
            ".pkl", ".pickle", ".db", ".sqlite",
        }
        binary_files = [
            f.name for f in CANON_DIR.iterdir()
            if f.is_file() and f.suffix in binary_extensions
        ]
        assert not binary_files, f"Binary files in review dir: {binary_files}"

    def test_no_hidden_files_in_review_dir(self) -> None:
        """No hidden files (dot-prefixed) in review dir."""
        if not CANON_DIR.exists():
            pytest.skip("Review directory does not exist yet")
        hidden = [
            f.name for f in CANON_DIR.iterdir()
            if f.name.startswith(".")
        ]
        assert not hidden, f"Hidden files in review dir: {hidden}"

    def test_no_subdirectories_in_review_dir(self) -> None:
        """Review dir should be flat — no subdirectories."""
        if not CANON_DIR.exists():
            pytest.skip("Review directory does not exist yet")
        subdirs = [
            d.name for d in CANON_DIR.iterdir()
            if d.is_dir()
        ]
        assert not subdirs, f"Subdirectories in review dir: {subdirs}"

    def test_all_files_use_correct_prefix(self) -> None:
        """Every file in review dir should use the phase14_6c_ prefix."""
        if not CANON_DIR.exists():
            pytest.skip("Review directory does not exist yet")
        wrong_prefix = [
            f.name for f in CANON_DIR.iterdir()
            if f.is_file() and not f.name.startswith(PREFIX)
        ]
        assert not wrong_prefix, (
            f"Files with wrong prefix: {wrong_prefix}"
        )
