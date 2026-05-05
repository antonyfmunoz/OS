# W-GWS-API-001 Canonical Contract Mapping

**Version:** v1
**Date:** 2026-05-05
**Mapping ID:** w_gws_api_001_canonical_contract_mapping

## Purpose

Maps Google Docs/Drive API output into CanonicalSourceRecord fields.
Encodes the tab-aware extraction requirements as verifiable constraints.

## API Requirements (12)

| # | Requirement ID | Description |
|---|---------------|-------------|
| 1 | include_tabs_content | includeTabsContent=true must be set on documents.get |
| 2 | document_tabs_traversal | traverse document.tabs array for all top-level tabs |
| 3 | child_tabs_recursion | recurse childTabs for all nested/child tabs |
| 4 | per_tab_body_extraction | collect body/content per tab via tab.documentTab.body |
| 5 | empty_tab_marking | mark tabs with no text content as empty |
| 6 | inaccessible_tab_marking | mark inaccessible content with reason |
| 7 | file_id_preservation | preserve file_id/document_id from Drive/Docs API |
| 8 | tab_id_preservation | preserve tab_id, title, and computed tab_path |
| 9 | backend_identity_preservation | preserve backend/access path identity in provenance |
| 10 | source_account_preservation | preserve source account/instance scope |
| 11 | canonical_source_record_emission | emit CanonicalSourceRecord per document |
| 12 | coverage_validation | validate coverage against expected doc/tab/child-tab/word counts |

All requirements are **required** and **verifiable**.

## Canonical Field Mappings

| Field | Mapping |
|-------|---------|
| file_id | Drive API file.id → CanonicalSourceRecord.file_id |
| title | Drive API file.name → CanonicalSourceRecord.title |
| tab_id | Docs API tab.tabProperties.tabId → TabSourceRecord.tab_id |
| tab_title | Docs API tab.tabProperties.title → TabSourceRecord.tab_title |
| tab_path | computed from nesting depth → TabSourceRecord.tab_path |
| parent_tab_id | tab.tabProperties.parentTabId → TabSourceRecord.parent_tab_id |
| is_empty | len(text_content) == 0 → TabSourceRecord.is_empty |
| text_content | tab.documentTab.body → TabSourceRecord.text_content |
| word_count | len(text_content.split()) → TabSourceRecord.word_count |
| backend_type | 'api' → ProvenanceRecord.backend_type |
| extraction_method | 'tab_aware_api' → ProvenanceRecord.extraction_method |
| content_came_from_api | True → ProvenanceRecord.content_came_from_api |

## Extraction Constraints

1. includeTabsContent=true is **non-negotiable**
2. first-tab-only extraction is **rejected as silent data loss**
3. document.body without tabs traversal is **rejected**
4. tabs without childTabs recursion is **incomplete**
5. empty tabs must be explicitly marked, not silently dropped
6. inaccessible content must carry a reason, not be silently ignored
7. word count must be computed per tab for parity validation
8. extraction timestamp must be recorded

## W0-001 Expected Coverage Contract

| Metric | Expected |
|--------|----------|
| Documents | 28 |
| Tabs | 321 |
| Child Tabs | 134 |
| Words | 283,831 |
| Instance ID | antony_empyrean |
| Global Canon Default | false |

## Verification Functions

| Function | What It Checks |
|----------|---------------|
| api_mapping_requires_include_tabs_content | include_tabs_content requirement is required |
| api_mapping_requires_document_tabs_traversal | document_tabs_traversal requirement is required |
| api_mapping_requires_child_tabs_recursion | child_tabs_recursion requirement is required |
| api_mapping_preserves_per_tab_provenance | tab_id, tab_title, tab_path, parent_tab_id all mapped |
| api_mapping_rejects_first_tab_only | extraction constraints reject first-tab-only |

## Module

`core/adapter_package_manager/google_workspace_api_contract_mapping.py`
