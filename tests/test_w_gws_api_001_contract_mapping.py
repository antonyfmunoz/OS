"""Tests for W-GWS-API-001 Canonical Contract Mapping.

Validates API requirements, field mappings, extraction constraints,
and coverage contract for the tab-aware extraction path.
"""

import sys
import unittest

sys.path.insert(0, "/opt/OS")

from core.adapter_package_manager.google_workspace_api_contract_mapping import (
    GoogleWorkspaceApiContractMapping,
    W0001ExpectedCoverageContract,
    api_mapping_preserves_per_tab_provenance,
    api_mapping_rejects_first_tab_only,
    api_mapping_requires_child_tabs_recursion,
    api_mapping_requires_document_tabs_traversal,
    api_mapping_requires_include_tabs_content,
    build_w0_001_expected_coverage_contract,
    build_w_gws_api_001_contract_mapping,
)


class TestContractMapping(unittest.TestCase):
    def setUp(self) -> None:
        self.mapping = build_w_gws_api_001_contract_mapping()

    def test_mapping_builds(self) -> None:
        self.assertIsInstance(self.mapping, GoogleWorkspaceApiContractMapping)

    def test_mapping_id(self) -> None:
        self.assertEqual(
            self.mapping.mapping_id,
            "w_gws_api_001_canonical_contract_mapping",
        )

    def test_requires_include_tabs_content(self) -> None:
        self.assertTrue(api_mapping_requires_include_tabs_content(self.mapping))

    def test_requires_document_tabs_traversal(self) -> None:
        self.assertTrue(
            api_mapping_requires_document_tabs_traversal(self.mapping)
        )

    def test_requires_child_tabs_recursion(self) -> None:
        self.assertTrue(api_mapping_requires_child_tabs_recursion(self.mapping))

    def test_preserves_per_tab_provenance(self) -> None:
        self.assertTrue(api_mapping_preserves_per_tab_provenance(self.mapping))

    def test_rejects_first_tab_only(self) -> None:
        self.assertTrue(api_mapping_rejects_first_tab_only(self.mapping))

    def test_has_12_api_requirements(self) -> None:
        self.assertEqual(len(self.mapping.api_requirements), 12)

    def test_all_requirements_are_required(self) -> None:
        for req in self.mapping.api_requirements:
            self.assertTrue(
                req.required,
                f"{req.requirement_id} should be required",
            )

    def test_all_requirements_are_verifiable(self) -> None:
        for req in self.mapping.api_requirements:
            self.assertTrue(
                req.verifiable,
                f"{req.requirement_id} should be verifiable",
            )

    def test_canonical_field_mappings_present(self) -> None:
        expected_fields = [
            "file_id",
            "title",
            "tab_id",
            "tab_title",
            "tab_path",
            "parent_tab_id",
            "is_empty",
            "text_content",
            "word_count",
            "backend_type",
            "extraction_method",
            "content_came_from_api",
        ]
        for f in expected_fields:
            self.assertIn(
                f,
                self.mapping.canonical_field_mappings,
                f"missing field mapping: {f}",
            )

    def test_extraction_constraints_present(self) -> None:
        self.assertTrue(len(self.mapping.extraction_constraints) >= 8)

    def test_include_tabs_content_non_negotiable(self) -> None:
        self.assertTrue(
            any(
                "non-negotiable" in c.lower()
                for c in self.mapping.extraction_constraints
            )
        )

    def test_to_dict_roundtrip(self) -> None:
        d = self.mapping.to_dict()
        self.assertEqual(
            d["mapping_id"], "w_gws_api_001_canonical_contract_mapping"
        )
        self.assertEqual(len(d["api_requirements"]), 12)
        self.assertIsInstance(d["canonical_field_mappings"], dict)


class TestW0001CoverageContract(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = build_w0_001_expected_coverage_contract()

    def test_contract_builds(self) -> None:
        self.assertIsInstance(self.contract, W0001ExpectedCoverageContract)

    def test_expected_docs_28(self) -> None:
        self.assertEqual(self.contract.expected_docs, 28)

    def test_expected_tabs_321(self) -> None:
        self.assertEqual(self.contract.expected_tabs, 321)

    def test_expected_child_tabs_134(self) -> None:
        self.assertEqual(self.contract.expected_child_tabs, 134)

    def test_expected_words_283831(self) -> None:
        self.assertEqual(self.contract.expected_words, 283831)

    def test_instance_id_antony_empyrean(self) -> None:
        self.assertEqual(self.contract.instance_id, "antony_empyrean")

    def test_global_canon_not_allowed_by_default(self) -> None:
        self.assertFalse(self.contract.global_canon_allowed_by_default)

    def test_coverage_contract_in_mapping(self) -> None:
        mapping = build_w_gws_api_001_contract_mapping()
        self.assertIsNotNone(mapping.coverage_contract)
        self.assertEqual(mapping.coverage_contract.expected_docs, 28)

    def test_to_dict(self) -> None:
        d = self.contract.to_dict()
        self.assertEqual(d["expected_docs"], 28)
        self.assertEqual(d["expected_tabs"], 321)
        self.assertFalse(d["global_canon_allowed_by_default"])


if __name__ == "__main__":
    unittest.main()
