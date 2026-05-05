# W-GWS-API-001 Reframe to Package Set

**Date:** 2026-05-05
**Status:** Reframed — preserved as provenance/alias

## What Changed

W-GWS-API-001 was originally modeled as a monolithic "Google Workspace
API Adapter Package" containing both Drive and Docs capabilities.

The founder clarified: Google Workspace should be an **Adapter Family**,
not a monolithic package. Each major Google product gets its own
Adapter Package.

## How W-GWS-API-001 Maps to the New Architecture

| W-GWS-API-001 Capability | New Package |
|--------------------------|------------|
| Google Drive inventory | W-GDRIVE-API-001 |
| Google Drive metadata | W-GDRIVE-API-001 |
| Folder/file identification | W-GDRIVE-API-001 |
| Google Docs tab-aware extraction | W-GDOCS-API-001 |
| Document.tabs traversal | W-GDOCS-API-001 |
| ChildTabs recursion | W-GDOCS-API-001 |
| Per-tab provenance | W-GDOCS-API-001 |
| Canonical source record emission | W-GDOCS-API-001 |
| W0-001 coverage validation | W-GDOCS-API-001 |
| Shared auth/OAuth | W-GWS-CORE-001 |
| Shared governance | W-GWS-CORE-001 |
| No-secret policy | W-GWS-CORE-001 |

## W-GWS-API-001 Preservation

The W-GWS-API-001 code and tests are **preserved** as-is.

- `core/adapter_package_manager/google_workspace_api_adapter_path.py` — unchanged
- `core/adapter_package_manager/google_workspace_api_contract_mapping.py` — unchanged
- `core/adapter_package_manager/google_workspace_api_governance.py` — unchanged
- `core/adapter_package_manager/google_workspace_api_maturity.py` — unchanged
- All 4 test files — unchanged, still passing

W-GWS-API-001 serves as:
1. **Provenance** — documents the original monolithic design
2. **Backward compatibility** — existing references still resolve
3. **Legacy alias** — new packages reference it via `legacy_provenance`

## What W-GWS-API-001 Is Now

A legacy composed W0-001 API slice that has been split into:
- W-GWS-CORE-001 (shared foundation)
- W-GDRIVE-API-001 (Drive capabilities)
- W-GDOCS-API-001 (Docs capabilities)

The 100% maturity achieved by W-GWS-API-001 transfers to the
new service packages because the capabilities, governance, and
contract mappings are preserved.
