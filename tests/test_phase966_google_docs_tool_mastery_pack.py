import sys
import os

sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")

import unittest
from eos_ai.substrate.adapter_engine_contracts import (
    ToolMasteryPack,
    tool_mastery_is_mature,
)


def build_google_docs_tool_mastery_pack() -> ToolMasteryPack:
    """Reference Google Docs Tool Mastery Pack for testing."""
    return ToolMasteryPack(
        adapter_id="google_docs_api",
        tool_name="Google Docs API",
        version_scope="documents.get v1 with tabs",
        best_practices=[
            "Always use includeTabsContent=true for full extraction",
            "Traverse document.tabs for all top-level tabs",
            "Recursively traverse childTabs for nested tabs",
            "Attribute body text to the correct tab",
            "Mark empty tabs as empty, not as extraction failures",
            "Compute word counts per tab and per document",
            "Preserve per-tab provenance in canonical records",
        ],
        common_workflows=[
            "Full tab-aware extraction: documents.get with includeTabsContent=true → traverse tabs → traverse childTabs → extract body per tab → mark empty → compute word counts → emit canonical record",
        ],
        anti_patterns=[
            "Reading only document.body without tab awareness",
            "Assuming one document equals one content body",
            "Ignoring tabs entirely",
            "Flattening tabs without preserving provenance",
            "Treating empty tabs as extraction failures",
            "Marking extraction complete without tab count validation",
            "Treating API success response as coverage success",
            "Treating CLI/MCP success as complete without proving all-tabs support",
        ],
        failure_modes=[
            "First-tab-only extraction: documents.get without includeTabsContent=true silently returns only first tab content",
            "Missing child tabs: not recursing into childTabs loses nested content",
            "Empty tab misclassification: marking empty tabs as failures rather than genuinely empty",
            "Foreground ownership block (Computer Use): cannot send keys to Chrome without foreground",
        ],
        recovery_playbooks=[
            "If first-tab-only detected: re-extract with includeTabsContent=true and recount words",
            "If child tabs missing: add recursive childTabs traversal and recount",
        ],
        hidden_features=[
            "Google Docs document tabs (introduced 2024): documents can have multiple content tabs",
            "Child tabs: tabs can contain nested child tabs forming a tree",
            "includeTabsContent parameter: must be explicitly set to true",
        ],
        api_defaults_and_traps=[
            "documents.get default does NOT include tab content — only first tab body appears in document.body",
            "includeTabsContent=true is NOT the default — must be explicitly requested",
            "document.body field exists even when tabs exist — it shows only the first tab, creating silent data loss",
        ],
        completeness_requirements=[
            "includeTabsContent=true used in all extraction calls",
            "All top-level tabs counted and extracted",
            "All child tabs counted recursively and extracted",
            "Per-tab text attributed correctly",
            "Empty tabs marked as empty",
            "Inaccessible tabs marked as inaccessible",
            "Per-tab provenance preserved in canonical records",
            "Total word count computed per tab and per document",
            "First-tab-only risk detection enabled",
            "Canonical source record emitted per document",
        ],
        validation_checklist=[
            "includeTabsContent=true confirmed in API call",
            "Top-level tab count matches expected",
            "Child tab count matches expected (recursive)",
            "Per-tab text extracted and non-empty (or marked empty)",
            "Empty tabs explicitly marked",
            "Inaccessible tabs explicitly marked",
            "Per-tab provenance recorded",
            "Total word count computed",
            "First-tab-only risk check passed",
            "Canonical source record emitted",
            "Parity comparator passed (doc count, tab count, child tab count, word count, provenance)",
        ],
        edge_cases=[
            "Document with 0 tabs (legacy pre-tabs document)",
            "Document with 100+ tabs",
            "Tab with empty body",
            "Child tab nested 3+ levels deep",
            "Tab created after initial extraction",
        ],
        quality_standards=[
            "95%+ word recall vs reference extraction",
            "100% tab count match",
            "100% child tab count match",
            "Zero silent data loss from first-tab-only default",
        ],
        last_verified="2026-05-05",
        provenance_notes="Derived from W0-001 tab-aware re-extraction (283,831 words, 321 tabs, 134 child tabs, 0 errors)",
    )


class TestGoogleDocsMasteryPackContent(unittest.TestCase):
    def setUp(self):
        self.pack = build_google_docs_tool_mastery_pack()

    def test_includes_include_tabs_content_requirement(self):
        all_text = " ".join(
            self.pack.best_practices
            + self.pack.completeness_requirements
            + self.pack.api_defaults_and_traps
        )
        assert "includeTabsContent" in all_text

    def test_includes_document_tabs_traversal(self):
        all_text = " ".join(self.pack.best_practices + self.pack.common_workflows)
        assert "document.tabs" in all_text or "traverse" in all_text.lower()

    def test_includes_child_tabs_recursion(self):
        all_text = " ".join(self.pack.best_practices + self.pack.completeness_requirements)
        assert "childTabs" in all_text or "child tabs" in all_text.lower()

    def test_includes_first_tab_only_risk(self):
        all_text = " ".join(
            self.pack.failure_modes + self.pack.anti_patterns + self.pack.api_defaults_and_traps
        )
        assert "first-tab-only" in all_text.lower() or "first tab" in all_text.lower()

    def test_includes_per_tab_provenance(self):
        all_text = " ".join(
            self.pack.best_practices
            + self.pack.completeness_requirements
            + self.pack.validation_checklist
        )
        assert "provenance" in all_text.lower()

    def test_includes_empty_tab_marking(self):
        all_text = " ".join(
            self.pack.best_practices + self.pack.completeness_requirements + self.pack.anti_patterns
        )
        assert "empty tab" in all_text.lower()

    def test_includes_parity_validation(self):
        all_text = " ".join(self.pack.validation_checklist)
        assert "parity" in all_text.lower()

    def test_pack_is_mature(self):
        assert tool_mastery_is_mature(self.pack)

    def test_has_anti_patterns(self):
        assert len(self.pack.anti_patterns) >= 5

    def test_has_completeness_requirements(self):
        assert len(self.pack.completeness_requirements) >= 5

    def test_has_validation_checklist(self):
        assert len(self.pack.validation_checklist) >= 5

    def test_has_api_defaults_and_traps(self):
        assert len(self.pack.api_defaults_and_traps) >= 2

    def test_has_hidden_features(self):
        assert len(self.pack.hidden_features) >= 2


if __name__ == "__main__":
    unittest.main()
