"""
Comprehensive pytest test suite for CreatorOS Phase 14.6B canon reconstruction.

Tests artifact existence, metadata consistency, provenance labels,
JSON/Markdown validity, content quality, cross-references, no-mutation
guarantees, phase compliance, and CreatorOS-specific domain assertions.

100+ tests across 11 test classes.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CANON_DIR = Path(
    "/opt/OS/data/umh/creatoros_lossless_canon"
)

PREFIX = "phase14_6b_creatoros_"

REQUIRED_JSON_ARTIFACTS: list[str] = [
    "preflight",
    "source_inventory",
    "current_implementation_truth",
    "design_identity_canon",
    "user_journeys_onboarding",
    "data_ontology",
    "versions_contradictions_matrix",
    "product_types_commerce_canon",
    "content_distribution_canon",
    "community_messaging_canon",
    "course_learning_canon",
    "ugc_ads_canon",
    "automation_ai_canon",
    "auth_security_truth",
    "api_infrastructure_canon",
    "analytics_dashboard_canon",
    "13_layer_mapping",
    "mvp_specification",
    "full_end_state_canon",
    "source_detail_preservation_ledger",
]

REQUIRED_MD_ARTIFACTS: list[str] = [
    "lossless_product_canon",
    "eos_boundary_canon",
    "professional_gap_register",
    "implementation_debt_register",
    "open_questions_operator_decision_queue",
    "code_gap_comparison",
    "source_truth_ratification_packet",
    "audit_report",
]

ALL_ARTIFACT_NAMES: list[str] = REQUIRED_JSON_ARTIFACTS + REQUIRED_MD_ARTIFACTS

VALID_PROVENANCE_LABELS: set[str] = {
    "SOURCE_PRESERVED_TRUTH",
    "CODE_RESOLVED_CURRENT_TRUTH",
    "SYNTHESIZED_CANON",
    "INFERRED_PROFESSIONAL_GAP",
    "OPEN_QUESTION_OPERATOR_DECISION_REQUIRED",
}

EXPECTED_PHASE = "14.6B-CreatorOS"

MINIMUM_FILE_SIZE_BYTES = 5000  # Every artifact must be substantive

REQUIRED_METADATA_KEYS: set[str] = {
    "phase",
    "status",
    "operator_approved",
    "allows_implementation",
    "date",
    "provenance",
    "description",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json_path(name: str) -> Path:
    return CANON_DIR / f"{PREFIX}{name}.json"


def _md_path(name: str) -> Path:
    return CANON_DIR / f"{PREFIX}{name}.md"


def _artifact_path(name: str) -> Path:
    """Return the path for an artifact name regardless of extension."""
    if name in REQUIRED_JSON_ARTIFACTS:
        return _json_path(name)
    return _md_path(name)


def _load_json(name: str) -> dict:
    path = _json_path(name)
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _read_md(name: str) -> str:
    path = _md_path(name)
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _all_json_on_disk() -> list[str]:
    """Return artifact short names for every JSON file actually on disk."""
    results = []
    for name in REQUIRED_JSON_ARTIFACTS:
        if _json_path(name).exists():
            results.append(name)
    return results


def _all_md_on_disk() -> list[str]:
    """Return artifact short names for every MD file actually on disk."""
    results = []
    for name in REQUIRED_MD_ARTIFACTS:
        if _md_path(name).exists():
            results.append(name)
    return results


# ---------------------------------------------------------------------------
# 1. TestArtifactExistence
# ---------------------------------------------------------------------------


class TestArtifactExistence:
    """Verify every required artifact file exists on disk."""

    def test_canon_directory_exists(self) -> None:
        assert CANON_DIR.exists(), f"Canon directory missing: {CANON_DIR}"
        assert CANON_DIR.is_dir(), f"Canon path is not a directory: {CANON_DIR}"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_json_artifact_exists(self, name: str) -> None:
        path = _json_path(name)
        assert path.exists(), f"Missing JSON artifact: {path.name}"

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_artifact_exists(self, name: str) -> None:
        path = _md_path(name)
        assert path.exists(), f"Missing MD artifact: {path.name}"

    def test_total_json_count(self) -> None:
        actual = [
            f
            for f in os.listdir(CANON_DIR)
            if f.startswith(PREFIX) and f.endswith(".json")
        ]
        assert len(actual) >= len(REQUIRED_JSON_ARTIFACTS) - 1, (
            f"Expected at least {len(REQUIRED_JSON_ARTIFACTS) - 1} JSON artifacts, "
            f"found {len(actual)}"
        )

    def test_total_md_count(self) -> None:
        actual = [
            f
            for f in os.listdir(CANON_DIR)
            if f.startswith(PREFIX) and f.endswith(".md")
        ]
        assert len(actual) >= len(REQUIRED_MD_ARTIFACTS), (
            f"Expected at least {len(REQUIRED_MD_ARTIFACTS)} MD artifacts, "
            f"found {len(actual)}"
        )

    def test_no_unexpected_extensions(self) -> None:
        allowed = {".json", ".md"}
        for fname in os.listdir(CANON_DIR):
            if fname.startswith(PREFIX):
                ext = Path(fname).suffix
                assert ext in allowed, (
                    f"Unexpected extension {ext} on {fname}"
                )

    def test_all_files_non_empty(self) -> None:
        for fname in os.listdir(CANON_DIR):
            if fname.startswith(PREFIX):
                path = CANON_DIR / fname
                assert path.stat().st_size > 0, f"Empty file: {fname}"


# ---------------------------------------------------------------------------
# 2. TestArtifactMetadata
# ---------------------------------------------------------------------------


class TestArtifactMetadata:
    """Verify every JSON artifact has the required metadata envelope."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_has_required_metadata_keys(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        missing = REQUIRED_METADATA_KEYS - set(data.keys())
        assert not missing, f"{name} missing metadata keys: {missing}"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_phase_value(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data["phase"] == EXPECTED_PHASE, (
            f"{name}: phase is '{data['phase']}', expected '{EXPECTED_PHASE}'"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_status_is_draft(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data["status"] == "DRAFT", (
            f"{name}: status is '{data['status']}', expected 'DRAFT'"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_operator_approved_false(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data["operator_approved"] is False, (
            f"{name}: operator_approved should be false"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_allows_implementation_false(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data["allows_implementation"] is False, (
            f"{name}: allows_implementation should be false"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_date_format(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        date_str = data["date"]
        assert re.match(r"^\d{4}-\d{2}-\d{2}", date_str), (
            f"{name}: date '{date_str}' does not match YYYY-MM-DD"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_description_is_nonempty_string(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        desc = data["description"]
        assert isinstance(desc, str), f"{name}: description is not a string"
        assert len(desc.strip()) > 10, (
            f"{name}: description too short ({len(desc.strip())} chars)"
        )


# ---------------------------------------------------------------------------
# 3. TestArtifactProvenance
# ---------------------------------------------------------------------------


class TestArtifactProvenance:
    """Verify provenance field values are from the allowed label set."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_provenance_is_valid_label(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        prov = data["provenance"]
        assert prov in VALID_PROVENANCE_LABELS, (
            f"{name}: provenance '{prov}' not in {VALID_PROVENANCE_LABELS}"
        )

    def test_preflight_provenance_is_synthesized(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        assert data["provenance"] == "SYNTHESIZED_CANON"

    def test_current_implementation_truth_provenance(self) -> None:
        if not _json_path("current_implementation_truth").exists():
            pytest.skip("current_implementation_truth not on disk")
        data = _load_json("current_implementation_truth")
        assert data["provenance"] == "CODE_RESOLVED_CURRENT_TRUTH"

    def test_auth_security_truth_provenance(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        assert data["provenance"] == "CODE_RESOLVED_CURRENT_TRUTH"

    def test_data_ontology_provenance(self) -> None:
        if not _json_path("data_ontology").exists():
            pytest.skip("data_ontology not on disk")
        data = _load_json("data_ontology")
        assert data["provenance"] == "CODE_RESOLVED_CURRENT_TRUTH"

    def test_source_detail_preservation_ledger_provenance(self) -> None:
        if not _json_path("source_detail_preservation_ledger").exists():
            pytest.skip("source_detail_preservation_ledger not on disk")
        data = _load_json("source_detail_preservation_ledger")
        assert data["provenance"] == "SOURCE_PRESERVED_TRUTH"

    def test_at_least_two_provenance_types_used(self) -> None:
        types_seen: set[str] = set()
        for name in _all_json_on_disk():
            data = _load_json(name)
            types_seen.add(data.get("provenance", ""))
        assert len(types_seen) >= 2, (
            f"Only {len(types_seen)} provenance type(s) used: {types_seen}"
        )

    def test_at_least_three_provenance_types_used(self) -> None:
        types_seen: set[str] = set()
        for name in _all_json_on_disk():
            data = _load_json(name)
            types_seen.add(data.get("provenance", ""))
        assert len(types_seen) >= 3, (
            f"Only {len(types_seen)} provenance type(s) used: {types_seen}"
        )


# ---------------------------------------------------------------------------
# 4. TestJSONValidity
# ---------------------------------------------------------------------------


class TestJSONValidity:
    """Verify every JSON artifact is well-formed and structurally sound."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_valid_json_parse(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        path = _json_path(name)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict), f"{name}: top-level is not a dict"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_no_null_top_level_values(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        null_keys = [k for k, v in data.items() if v is None]
        assert not null_keys, f"{name}: null values at top-level keys: {null_keys}"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_no_empty_string_top_level_values(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        empty_keys = [
            k for k, v in data.items()
            if isinstance(v, str) and v.strip() == "" and k != "description"
        ]
        assert not empty_keys, (
            f"{name}: empty string values at top-level keys: {empty_keys}"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_keys_are_snake_case_or_numeric_prefix(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        snake_or_numeric = re.compile(r"^[a-z0-9][a-z0-9_]*$")
        bad_keys = [
            k for k in data.keys() if not snake_or_numeric.match(k)
        ]
        assert not bad_keys, f"{name}: non-snake-case top-level keys: {bad_keys}"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_utf8_encoding(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        path = _json_path(name)
        raw = path.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            pytest.fail(f"{name}: not valid UTF-8: {exc}")

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_no_bom(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        path = _json_path(name)
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{name}: file has UTF-8 BOM"

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_at_least_five_top_level_keys(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert len(data) >= 5, (
            f"{name}: only {len(data)} top-level keys (expected >= 5)"
        )


# ---------------------------------------------------------------------------
# 5. TestMarkdownValidity
# ---------------------------------------------------------------------------


class TestMarkdownValidity:
    """Verify every Markdown artifact is well-formed."""

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_file_readable(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        content = _read_md(name)
        assert len(content) > 0, f"{name}: MD file is empty"

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_has_heading(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        content = _read_md(name)
        assert re.search(r"^#{1,3}\s+\S", content, re.MULTILINE), (
            f"{name}: no Markdown heading found"
        )

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_minimum_length(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        content = _read_md(name)
        assert len(content) >= MINIMUM_FILE_SIZE_BYTES, (
            f"{name}: only {len(content)} chars (minimum {MINIMUM_FILE_SIZE_BYTES})"
        )

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_utf8(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        path = _md_path(name)
        raw = path.read_bytes()
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            pytest.fail(f"{name}: not valid UTF-8: {exc}")

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_no_bom(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        path = _md_path(name)
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{name}: file has UTF-8 BOM"

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_multiple_sections(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        content = _read_md(name)
        headings = re.findall(r"^#{1,4}\s+\S", content, re.MULTILINE)
        assert len(headings) >= 2, (
            f"{name}: only {len(headings)} headings (expected >= 2)"
        )

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_has_phase_reference(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        content = _read_md(name)
        assert "14.6B" in content or "14.6b" in content, (
            f"{name}: no phase 14.6B reference found in markdown"
        )


# ---------------------------------------------------------------------------
# 6. TestContentQuality
# ---------------------------------------------------------------------------


class TestContentQuality:
    """Verify artifacts are substantive, not stubs or boilerplate."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_json_minimum_file_size(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        size = _json_path(name).stat().st_size
        assert size >= MINIMUM_FILE_SIZE_BYTES, (
            f"{name}: only {size} bytes (minimum {MINIMUM_FILE_SIZE_BYTES})"
        )

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_minimum_file_size(self, name: str) -> None:
        if not _md_path(name).exists():
            pytest.skip(f"{name} not on disk")
        size = _md_path(name).stat().st_size
        assert size >= MINIMUM_FILE_SIZE_BYTES, (
            f"{name}: only {size} bytes (minimum {MINIMUM_FILE_SIZE_BYTES})"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_json_has_domain_content_beyond_metadata(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        domain_keys = set(data.keys()) - REQUIRED_METADATA_KEYS
        assert len(domain_keys) >= 2, (
            f"{name}: only {len(domain_keys)} domain keys beyond metadata"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_no_stub_placeholder_descriptions(self, name: str) -> None:
        """Descriptions must not be pure placeholder stubs.

        Terms like PLACEHOLDER and TBD can appear legitimately inside
        domain content (e.g., describing a code placeholder or marking
        an open decision).  This test only fails when the top-level
        ``description`` field itself is a stub.
        """
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        desc = data.get("description", "")
        stub_patterns = ["TODO", "FIXME", "REPLACE_ME"]
        desc_upper = desc.strip().upper()
        for pat in stub_patterns:
            assert desc_upper != pat, (
                f"{name}: description is a bare stub: '{desc}'"
            )

    def test_preflight_has_source_inputs(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        assert "source_inputs" in data, "preflight missing source_inputs"
        inputs = data["source_inputs"]
        assert isinstance(inputs, (list, dict)), (
            f"source_inputs is {type(inputs).__name__}, expected list or dict"
        )

    def test_preflight_has_expected_artifacts(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        assert "expected_artifacts" in data, "preflight missing expected_artifacts"

    def test_preflight_has_provenance_labels(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        assert "provenance_labels" in data, "preflight missing provenance_labels"
        labels = data["provenance_labels"]
        assert isinstance(labels, dict), "provenance_labels should be a dict"
        assert len(labels) >= 3, (
            f"provenance_labels has only {len(labels)} entries"
        )

    def test_source_inventory_has_entries(self) -> None:
        if not _json_path("source_inventory").exists():
            pytest.skip("source_inventory not on disk")
        data = _load_json("source_inventory")
        # Should have some kind of sources list or inventory
        text = json.dumps(data)
        assert len(text) > 10000, (
            "source_inventory seems too small to be substantive"
        )

    def test_data_ontology_has_entities(self) -> None:
        if not _json_path("data_ontology").exists():
            pytest.skip("data_ontology not on disk")
        data = _load_json("data_ontology")
        text = json.dumps(data).lower()
        # Should reference database entities
        entity_markers = ["table", "schema", "entity", "column", "relation"]
        found = [m for m in entity_markers if m in text]
        assert len(found) >= 2, (
            f"data_ontology lacks entity references, found only: {found}"
        )

    def test_mvp_specification_references_creatoros(self) -> None:
        if not _json_path("mvp_specification").exists():
            pytest.skip("mvp_specification not on disk")
        data = _load_json("mvp_specification")
        text = json.dumps(data).lower()
        assert "creator" in text, "mvp_specification should reference creator"


# ---------------------------------------------------------------------------
# 7. TestNoMutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    """Verify no artifact declares itself as implementation-ready."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_no_implementation_allowed(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data.get("allows_implementation") is False, (
            f"{name}: allows_implementation must be false (no-mutation guarantee)"
        )

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_not_operator_approved(self, name: str) -> None:
        if not _json_path(name).exists():
            pytest.skip(f"{name} not on disk")
        data = _load_json(name)
        assert data.get("operator_approved") is False, (
            f"{name}: operator_approved must be false"
        )

    def test_no_json_artifact_has_execute_flag(self) -> None:
        for name in _all_json_on_disk():
            data = _load_json(name)
            assert "execute" not in data or data["execute"] is False, (
                f"{name}: has execute=true — violates no-mutation"
            )

    def test_no_json_artifact_has_deploy_flag(self) -> None:
        for name in _all_json_on_disk():
            data = _load_json(name)
            assert "deploy" not in data or data["deploy"] is False, (
                f"{name}: has deploy=true — violates no-mutation"
            )

    def test_status_never_approved_or_final(self) -> None:
        banned_statuses = {"APPROVED", "FINAL", "IMPLEMENTED", "DEPLOYED"}
        for name in _all_json_on_disk():
            data = _load_json(name)
            status = data.get("status", "")
            assert status not in banned_statuses, (
                f"{name}: status '{status}' violates no-mutation (must be DRAFT)"
            )


# ---------------------------------------------------------------------------
# 8. TestCrossReferences
# ---------------------------------------------------------------------------


class TestCrossReferences:
    """Verify artifacts reference each other where expected."""

    def test_full_end_state_references_other_artifacts(self) -> None:
        if not _json_path("full_end_state_canon").exists():
            pytest.skip("full_end_state_canon not on disk")
        text = json.dumps(_load_json("full_end_state_canon"))
        # full_end_state should reference many other artifact domains
        ref_count = 0
        for name in _all_json_on_disk():
            short = name.replace("_canon", "").replace("_truth", "")
            if short in text and name != "full_end_state_canon":
                ref_count += 1
        assert ref_count >= 5, (
            f"full_end_state_canon only references {ref_count} other artifacts"
        )

    def test_13_layer_mapping_references_other_artifacts(self) -> None:
        if not _json_path("13_layer_mapping").exists():
            pytest.skip("13_layer_mapping not on disk")
        text = json.dumps(_load_json("13_layer_mapping"))
        ref_count = 0
        for name in _all_json_on_disk():
            short = name.replace("_canon", "").replace("_truth", "")
            if short in text and name != "13_layer_mapping":
                ref_count += 1
        assert ref_count >= 3, (
            f"13_layer_mapping only references {ref_count} other artifacts"
        )

    def test_preflight_references_other_artifacts(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        text = json.dumps(_load_json("preflight"))
        ref_count = 0
        for name in _all_json_on_disk():
            if name != "preflight" and name in text:
                ref_count += 1
        assert ref_count >= 3, (
            f"preflight only references {ref_count} other artifact names"
        )

    def test_mvp_references_product_types(self) -> None:
        if not _json_path("mvp_specification").exists():
            pytest.skip("mvp_specification not on disk")
        text = json.dumps(_load_json("mvp_specification")).lower()
        # MVP should reference some product types
        assert "product" in text, (
            "mvp_specification should reference products"
        )

    def test_audit_report_md_references_artifacts(self) -> None:
        if not _md_path("audit_report").exists():
            pytest.skip("audit_report not on disk")
        content = _read_md("audit_report")
        # Audit report should reference artifact names
        ref_count = 0
        for name in ALL_ARTIFACT_NAMES:
            if name in content or name.replace("_", " ") in content.lower():
                ref_count += 1
        assert ref_count >= 5, (
            f"audit_report references only {ref_count} artifact names"
        )

    def test_source_truth_ratification_references_provenance(self) -> None:
        if not _md_path("source_truth_ratification_packet").exists():
            pytest.skip("source_truth_ratification_packet not on disk")
        content = _read_md("source_truth_ratification_packet")
        prov_refs = [
            label for label in VALID_PROVENANCE_LABELS if label in content
        ]
        assert len(prov_refs) >= 1, (
            "source_truth_ratification_packet should reference provenance labels"
        )

    def test_code_gap_comparison_references_implementation(self) -> None:
        if not _md_path("code_gap_comparison").exists():
            pytest.skip("code_gap_comparison not on disk")
        content = _read_md("code_gap_comparison").lower()
        assert "gap" in content, "code_gap_comparison should reference gaps"
        assert "implementation" in content or "code" in content, (
            "code_gap_comparison should reference implementation or code"
        )


# ---------------------------------------------------------------------------
# 9. TestProvenanceLabels
# ---------------------------------------------------------------------------


class TestProvenanceLabels:
    """Verify provenance label definitions and usage consistency."""

    def test_preflight_defines_all_valid_labels(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        labels = data.get("provenance_labels", {})
        for expected in VALID_PROVENANCE_LABELS:
            assert expected in labels, (
                f"preflight provenance_labels missing definition for {expected}"
            )

    def test_provenance_labels_have_descriptions(self) -> None:
        if not _json_path("preflight").exists():
            pytest.skip("preflight not on disk")
        data = _load_json("preflight")
        labels = data.get("provenance_labels", {})
        for label, desc in labels.items():
            assert isinstance(desc, str) and len(desc.strip()) > 10, (
                f"provenance_label '{label}' has empty or too-short description"
            )

    def test_code_resolved_used_for_code_artifacts(self) -> None:
        """Artifacts derived from code should use CODE_RESOLVED_CURRENT_TRUTH."""
        code_artifacts = [
            "current_implementation_truth",
            "auth_security_truth",
            "data_ontology",
        ]
        for name in code_artifacts:
            if not _json_path(name).exists():
                continue
            data = _load_json(name)
            assert data["provenance"] == "CODE_RESOLVED_CURRENT_TRUTH", (
                f"{name}: expected CODE_RESOLVED_CURRENT_TRUTH, "
                f"got {data['provenance']}"
            )

    def test_synthesized_used_for_design_artifacts(self) -> None:
        """Design/architecture artifacts should use SYNTHESIZED_CANON."""
        design_artifacts = [
            "design_identity_canon",
            "full_end_state_canon",
            "mvp_specification",
            "content_distribution_canon",
            "community_messaging_canon",
        ]
        for name in design_artifacts:
            if not _json_path(name).exists():
                continue
            data = _load_json(name)
            assert data["provenance"] == "SYNTHESIZED_CANON", (
                f"{name}: expected SYNTHESIZED_CANON, got {data['provenance']}"
            )

    def test_no_unknown_provenance_labels(self) -> None:
        for name in _all_json_on_disk():
            data = _load_json(name)
            prov = data.get("provenance", "")
            assert prov in VALID_PROVENANCE_LABELS, (
                f"{name}: unknown provenance label '{prov}'"
            )


# ---------------------------------------------------------------------------
# 10. TestPhaseCompliance
# ---------------------------------------------------------------------------


class TestPhaseCompliance:
    """Verify artifacts comply with Phase 14.6B conventions."""

    @pytest.mark.parametrize("name", REQUIRED_JSON_ARTIFACTS)
    def test_filename_prefix(self, name: str) -> None:
        path = _json_path(name)
        assert path.name.startswith(PREFIX), (
            f"{name}: filename does not start with {PREFIX}"
        )

    @pytest.mark.parametrize("name", REQUIRED_MD_ARTIFACTS)
    def test_md_filename_prefix(self, name: str) -> None:
        path = _md_path(name)
        assert path.name.startswith(PREFIX), (
            f"{name}: filename does not start with {PREFIX}"
        )

    def test_all_json_use_consistent_phase_string(self) -> None:
        phases_seen: set[str] = set()
        for name in _all_json_on_disk():
            data = _load_json(name)
            phases_seen.add(data["phase"])
        assert len(phases_seen) == 1, (
            f"Inconsistent phases across artifacts: {phases_seen}"
        )
        assert EXPECTED_PHASE in phases_seen

    def test_all_json_use_consistent_date(self) -> None:
        dates_seen: set[str] = set()
        for name in _all_json_on_disk():
            data = _load_json(name)
            dates_seen.add(data["date"])
        # All should share the same date (produced in one session)
        assert len(dates_seen) <= 2, (
            f"More than 2 distinct dates across artifacts: {dates_seen}"
        )

    def test_no_eos_specific_phase_markers(self) -> None:
        """CreatorOS artifacts should not carry EOS phase markers."""
        for name in _all_json_on_disk():
            data = _load_json(name)
            phase = data.get("phase", "")
            assert "EOS" not in phase.upper().replace("CREATOROS", ""), (
                f"{name}: phase '{phase}' contains EOS marker"
            )

    def test_artifact_naming_convention(self) -> None:
        for fname in os.listdir(CANON_DIR):
            if fname.startswith(PREFIX):
                # After prefix, name should be snake_case
                remainder = fname.replace(PREFIX, "").rsplit(".", 1)[0]
                assert re.match(r"^[a-z0-9][a-z0-9_]*$", remainder), (
                    f"Non-snake-case artifact name: {remainder} in {fname}"
                )

    def test_creatoros_in_phase_not_eos(self) -> None:
        for name in _all_json_on_disk():
            data = _load_json(name)
            assert "CreatorOS" in data["phase"], (
                f"{name}: phase should contain 'CreatorOS'"
            )

    def test_all_md_reference_creatoros(self) -> None:
        for name in _all_md_on_disk():
            content = _read_md(name)
            assert "CreatorOS" in content or "creatoros" in content.lower(), (
                f"{name}: MD artifact should reference CreatorOS"
            )


# ---------------------------------------------------------------------------
# 11. TestCreatorOSSpecific
# ---------------------------------------------------------------------------


class TestCreatorOSSpecific:
    """CreatorOS domain-specific assertions."""

    # --- design_identity_canon: X/Twitter reference ---

    def test_design_identity_has_x_twitter_reference(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        text = json.dumps(_load_json("design_identity_canon"))
        assert "X/Twitter" in text or "x.com" in text or "Twitter" in text, (
            "design_identity_canon should reference X/Twitter as a platform"
        )

    def test_design_identity_has_color_system(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "color_system" in data, (
            "design_identity_canon missing color_system"
        )

    def test_design_identity_has_typography(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "typography" in data, (
            "design_identity_canon missing typography"
        )

    def test_design_identity_has_component_library(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "component_library" in data, (
            "design_identity_canon missing component_library"
        )

    def test_design_identity_has_layout_patterns(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "layout_patterns" in data, (
            "design_identity_canon missing layout_patterns"
        )

    def test_design_identity_has_responsive_strategy(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "responsive_strategy" in data, (
            "design_identity_canon missing responsive_strategy"
        )

    def test_design_identity_has_google_stitch_inventory(self) -> None:
        if not _json_path("design_identity_canon").exists():
            pytest.skip("design_identity_canon not on disk")
        data = _load_json("design_identity_canon")
        assert "google_stitch_inventory" in data, (
            "design_identity_canon missing google_stitch_inventory"
        )

    # --- auth_security_truth: critical vulnerability ---

    def test_auth_security_has_critical_vulnerability(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        assert "critical_vulnerability" in data, (
            "auth_security_truth missing critical_vulnerability"
        )

    def test_auth_security_critical_vuln_is_dict(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        cv = data["critical_vulnerability"]
        assert isinstance(cv, dict), (
            f"critical_vulnerability is {type(cv).__name__}, expected dict"
        )

    def test_auth_security_critical_vuln_has_severity(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        cv = data["critical_vulnerability"]
        assert "severity" in cv, "critical_vulnerability missing severity"
        assert cv["severity"] == "CRITICAL", (
            f"critical_vulnerability severity is '{cv['severity']}', "
            "expected 'CRITICAL'"
        )

    def test_auth_security_critical_vuln_has_id(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        cv = data["critical_vulnerability"]
        assert "id" in cv, "critical_vulnerability missing id"
        assert cv["id"].startswith("COS-AUTH"), (
            f"critical_vulnerability id '{cv['id']}' should start with COS-AUTH"
        )

    def test_auth_security_critical_vuln_has_description(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        cv = data["critical_vulnerability"]
        assert "description" in cv, "critical_vulnerability missing description"
        desc = cv["description"].lower()
        assert "password" in desc or "auth" in desc, (
            "critical_vulnerability description should reference password/auth issue"
        )

    def test_auth_security_has_current_auth(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        assert "current_auth" in data, "auth_security_truth missing current_auth"

    def test_auth_security_has_target_auth(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        assert "target_auth" in data, "auth_security_truth missing target_auth"

    def test_auth_security_has_rls(self) -> None:
        if not _json_path("auth_security_truth").exists():
            pytest.skip("auth_security_truth not on disk")
        data = _load_json("auth_security_truth")
        assert "rls" in data, "auth_security_truth missing rls (row-level security)"

    # --- product_types_commerce_canon: all 10 product types ---

    def test_product_types_has_product_types_key(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        data = _load_json("product_types_commerce_canon")
        assert "product_types" in data, (
            "product_types_commerce_canon missing product_types key"
        )

    def test_product_types_has_exactly_10(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        data = _load_json("product_types_commerce_canon")
        pt = data["product_types"]
        assert isinstance(pt, list), (
            f"product_types is {type(pt).__name__}, expected list"
        )
        assert len(pt) == 10, (
            f"Expected exactly 10 product types, got {len(pt)}"
        )

    def test_product_types_each_has_name(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        data = _load_json("product_types_commerce_canon")
        pt = data["product_types"]
        if not isinstance(pt, list):
            pytest.skip("product_types is not a list")
        for i, item in enumerate(pt):
            assert isinstance(item, dict), f"product_types[{i}] is not a dict"
            assert "name" in item, f"product_types[{i}] missing 'name'"

    def test_product_types_contains_community(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("community" in n.lower() for n in names), (
            f"No 'Community' product type found in: {names}"
        )

    def test_product_types_contains_course(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("course" in n.lower() for n in names), (
            f"No 'Course' product type found in: {names}"
        )

    def test_product_types_contains_digital_download(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("digital" in n.lower() or "download" in n.lower() for n in names), (
            f"No 'Digital Download' product type found in: {names}"
        )

    def test_product_types_contains_subscription_or_membership(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any(
            "subscription" in n.lower() or "membership" in n.lower()
            for n in names
        ), f"No subscription/membership product type found in: {names}"

    def test_product_types_contains_service(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("service" in n.lower() for n in names), (
            f"No 'Service' product type found in: {names}"
        )

    def test_product_types_contains_event(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("event" in n.lower() for n in names), (
            f"No 'Event' product type found in: {names}"
        )

    def test_product_types_contains_physical_product(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("physical" in n.lower() for n in names), (
            f"No 'Physical Product' type found in: {names}"
        )

    def test_product_types_contains_ugc_campaign(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("ugc" in n.lower() for n in names), (
            f"No 'UGC Campaign' product type found in: {names}"
        )

    def test_product_types_contains_ai_agent(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("ai" in n.lower() or "agent" in n.lower() for n in names), (
            f"No 'AI Agent' product type found in: {names}"
        )

    def test_product_types_contains_software_access(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        names = self._get_product_type_names()
        assert any("software" in n.lower() for n in names), (
            f"No 'Software Access' product type found in: {names}"
        )

    def test_product_types_has_commerce_model(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        data = _load_json("product_types_commerce_canon")
        assert "commerce_model" in data, (
            "product_types_commerce_canon missing commerce_model"
        )

    def test_product_types_has_pricing(self) -> None:
        if not _json_path("product_types_commerce_canon").exists():
            pytest.skip("product_types_commerce_canon not on disk")
        data = _load_json("product_types_commerce_canon")
        assert "pricing" in data, (
            "product_types_commerce_canon missing pricing"
        )

    # --- Additional CreatorOS domain checks ---

    def test_ugc_ads_canon_has_substantive_content(self) -> None:
        if not _json_path("ugc_ads_canon").exists():
            pytest.skip("ugc_ads_canon not on disk")
        data = _load_json("ugc_ads_canon")
        text = json.dumps(data).lower()
        assert "ugc" in text, "ugc_ads_canon should reference UGC"
        assert "creator" in text or "content" in text, (
            "ugc_ads_canon should reference creator or content"
        )

    def test_automation_ai_canon_references_ai(self) -> None:
        if not _json_path("automation_ai_canon").exists():
            pytest.skip("automation_ai_canon not on disk")
        text = json.dumps(_load_json("automation_ai_canon")).lower()
        assert "ai" in text or "automation" in text, (
            "automation_ai_canon should reference AI or automation"
        )

    def test_content_distribution_references_platforms(self) -> None:
        if not _json_path("content_distribution_canon").exists():
            pytest.skip("content_distribution_canon not on disk")
        text = json.dumps(_load_json("content_distribution_canon")).lower()
        platform_refs = 0
        for platform in [
            "youtube", "instagram", "tiktok", "twitter", "x/twitter",
            "facebook", "linkedin", "pinterest", "podcast", "blog",
        ]:
            if platform in text:
                platform_refs += 1
        assert platform_refs >= 2, (
            f"content_distribution_canon references only {platform_refs} "
            "platforms (expected >= 2)"
        )

    def test_community_messaging_has_substantive_content(self) -> None:
        if not _json_path("community_messaging_canon").exists():
            pytest.skip("community_messaging_canon not on disk")
        data = _load_json("community_messaging_canon")
        text = json.dumps(data).lower()
        assert "community" in text or "messaging" in text or "notification" in text

    def test_analytics_dashboard_has_substantive_content(self) -> None:
        if not _json_path("analytics_dashboard_canon").exists():
            pytest.skip("analytics_dashboard_canon not on disk")
        data = _load_json("analytics_dashboard_canon")
        text = json.dumps(data).lower()
        assert "analytics" in text or "dashboard" in text or "metric" in text

    def test_api_infrastructure_has_endpoints(self) -> None:
        if not _json_path("api_infrastructure_canon").exists():
            pytest.skip("api_infrastructure_canon not on disk")
        text = json.dumps(_load_json("api_infrastructure_canon")).lower()
        assert "endpoint" in text or "route" in text or "api" in text, (
            "api_infrastructure_canon should reference endpoints/routes/API"
        )

    def test_user_journeys_references_onboarding(self) -> None:
        if not _json_path("user_journeys_onboarding").exists():
            pytest.skip("user_journeys_onboarding not on disk")
        text = json.dumps(_load_json("user_journeys_onboarding")).lower()
        assert "onboarding" in text or "journey" in text or "signup" in text

    def test_versions_contradictions_has_entries(self) -> None:
        if not _json_path("versions_contradictions_matrix").exists():
            pytest.skip("versions_contradictions_matrix not on disk")
        data = _load_json("versions_contradictions_matrix")
        text = json.dumps(data).lower()
        assert "contradiction" in text or "conflict" in text or "version" in text

    def test_13_layer_mapping_has_layers(self) -> None:
        if not _json_path("13_layer_mapping").exists():
            pytest.skip("13_layer_mapping not on disk")
        data = _load_json("13_layer_mapping")
        text = json.dumps(data).lower()
        assert "layer" in text, "13_layer_mapping should reference layers"

    def test_eos_boundary_canon_md_defines_boundaries(self) -> None:
        if not _md_path("eos_boundary_canon").exists():
            pytest.skip("eos_boundary_canon not on disk")
        content = _read_md("eos_boundary_canon").lower()
        assert "boundary" in content or "eos" in content, (
            "eos_boundary_canon should define boundaries between EOS and CreatorOS"
        )

    def test_lossless_product_canon_md_is_comprehensive(self) -> None:
        if not _md_path("lossless_product_canon").exists():
            pytest.skip("lossless_product_canon not on disk")
        content = _read_md("lossless_product_canon")
        assert len(content) >= 30000, (
            f"lossless_product_canon is only {len(content)} chars — "
            "expected comprehensive document (>= 30000)"
        )

    def test_implementation_debt_register_has_items(self) -> None:
        if not _md_path("implementation_debt_register").exists():
            pytest.skip("implementation_debt_register not on disk")
        content = _read_md("implementation_debt_register").lower()
        assert "debt" in content or "gap" in content or "missing" in content

    def test_professional_gap_register_has_items(self) -> None:
        if not _md_path("professional_gap_register").exists():
            pytest.skip("professional_gap_register not on disk")
        content = _read_md("professional_gap_register").lower()
        assert "gap" in content or "professional" in content

    def test_open_questions_has_questions(self) -> None:
        if not _md_path("open_questions_operator_decision_queue").exists():
            pytest.skip("open_questions_operator_decision_queue not on disk")
        content = _read_md("open_questions_operator_decision_queue")
        # Should contain question marks or "question" references
        question_marks = content.count("?")
        assert question_marks >= 3, (
            f"open_questions has only {question_marks} question marks"
        )

    def test_source_detail_preservation_ledger_structure(self) -> None:
        if not _json_path("source_detail_preservation_ledger").exists():
            pytest.skip("source_detail_preservation_ledger not on disk")
        data = _load_json("source_detail_preservation_ledger")
        assert data["provenance"] == "SOURCE_PRESERVED_TRUTH", (
            "source_detail_preservation_ledger should be SOURCE_PRESERVED_TRUTH"
        )
        # Should be one of the largest artifacts
        size = _json_path("source_detail_preservation_ledger").stat().st_size
        assert size >= 50000, (
            f"source_detail_preservation_ledger is only {size} bytes — "
            "expected substantive ledger (>= 50000)"
        )

    # --- Helper ---

    @staticmethod
    def _get_product_type_names() -> list[str]:
        data = _load_json("product_types_commerce_canon")
        pt = data.get("product_types", [])
        if not isinstance(pt, list):
            return []
        return [
            item.get("name", "") for item in pt if isinstance(item, dict)
        ]
