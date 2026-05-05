# Google Workspace API Tab-Aware Adapter Path (W-GWS-API-001)

**Version:** v1
**Date:** 2026-05-05
**Status:** 100% Mature (Declared Path)

## Path Identity

| Field | Value |
|-------|-------|
| Path ID | W-GWS-API-001 |
| Package ID | google_workspace |
| Path Name | Google Workspace API Tab-Aware Extractor |
| Path Type | API |
| Declaration Status | DECLARED |
| Current Status | complete |
| Target Maturity | 100% |

## Supported Capabilities

1. `google_drive_inventory` — enumerate Drive files
2. `google_drive_metadata_extraction` — extract file metadata
3. `google_docs_tab_aware_extraction` — extract with includeTabsContent=true
4. `google_docs_child_tab_traversal` — recurse childTabs at all depths
5. `canonical_source_record_emission` — emit CanonicalSourceRecord per document
6. `source_graph_generation_support` — feed source graph builder
7. `ingestion_coverage_validation` — validate against expected counts

## Auth Method

`OAUTH_USER_CONSENT_OPAQUE_TOKEN_CACHE` — user-consented OAuth token,
cached opaquely. No token values are ever logged, stored in memory,
or promoted beyond the execution scope.

## References

| Component | Reference |
|-----------|-----------|
| Tool Mastery Pack | google_docs_tool_mastery_pack |
| Governance Policy | w_gws_api_001_governance_policy |
| Canonical Contract | w_gws_api_001_canonical_contract_mapping |

## Excluded Gaps

These are not part of this path's maturity obligation:

- CU parity remains separate path (W-GWS-CU-001)
- MCP remains candidate path
- CLI direct remains candidate path
- Export remains approval path

## Known Gaps

None. Path is 100% mature.

## Test Coverage

- test_w_gws_api_001_adapter_path
- test_w_gws_api_001_contract_mapping
- test_w_gws_api_001_governance
- test_w_gws_api_001_maturity

## Module

`core/adapter_package_manager/google_workspace_api_adapter_path.py`
