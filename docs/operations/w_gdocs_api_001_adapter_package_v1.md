# W-GDOCS-API-001: Google Docs API Adapter Package

**Version:** v1
**Date:** 2026-05-05
**Package ID:** W-GDOCS-API-001
**Status:** 100% Mature

## Purpose

Google Docs tab-aware extraction for W0-001.
Derived from W-GWS-API-001 where applicable.

## Capabilities

| Capability | Description |
|-----------|-------------|
| documents_get_with_include_tabs_content | includeTabsContent=true |
| document_tabs_traversal | Traverse document.tabs array |
| child_tabs_recursive_traversal | Recurse childTabs |
| per_tab_content_extraction | Extract body per tab |
| empty_tab_marking | Mark empty tabs explicitly |
| inaccessible_content_marking | Mark inaccessible content with reason |
| per_tab_provenance | Track tab-level provenance |
| canonical_source_record_emission | Emit CanonicalSourceRecord |
| w0_001_coverage_validation | Validate against expected counts |

## W0-001 Coverage Contract

| Metric | Expected |
|--------|----------|
| Documents | 28 |
| Tabs | 321 |
| Child Tabs | 134 |
| Words | 283,831 |

## Governance

- Read-only
- No edits/deletes/moves/shares
- No permission changes
- No export/download unless approved
- No credential capture
- No memory promotion

## Tab-Aware Requirements

1. `includeTabsContent=true` is non-negotiable
2. First-tab-only extraction is rejected as silent data loss
3. `document.body` without tabs traversal is rejected
4. Tabs without childTabs recursion is incomplete

## Legacy Provenance

Derived from W-GWS-API-001. The original monolithic Google Workspace
API adapter path has been split into Drive API + Docs API service
packages. This package inherits the Docs-related capabilities.

## Module

`core/adapter_package_manager/google_docs_api_package.py`
