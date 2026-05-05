# Phase 96.7D Report: Google Workspace Adapter Family Refactor + W0-001 Package Set

**Date:** 2026-05-05
**Phase:** 96.7D
**Status:** Complete

## 1. Founder Correction

The founder clarified: Google Workspace should NOT be modeled as one
monolithic Adapter Package. Google Workspace is an Adapter Family /
suite-level ecosystem. Each major Google product gets its own
Adapter Package.

## 2. Why Google Workspace Should Be an Adapter Family

A monolithic "Google Workspace Adapter Package" would:
- Conflate Drive maturity with Docs maturity
- Force Gmail/Sheets/Slides to block Drive/Docs tests
- Hide service-specific gaps behind aggregate numbers
- Prevent honest per-service maturity reporting
- Force all services into a single governance policy

## 3. Why Each Product Gets Its Own Package

- Drive has different capabilities than Docs
- Docs tab-aware extraction has specific API requirements
- Gmail would have entirely different governance (read vs compose)
- Each service needs its own Tool Mastery Pack
- Maturity should be per-service, not per-suite

## 4. Google Workspace Core Foundation Package

W-GWS-CORE-001 provides shared:
- Auth/session model (OAuth, browser profile, service account)
- No-secret policy (6 constraints)
- Governance defaults (9 rules)
- Rate limit doctrine (4 rules)
- Workspace-level Tool Mastery

Mature for W0-001 scope. Does NOT imply Gmail/Sheets/Slides maturity.

## 5. Google Drive API Package

W-GDRIVE-API-001: Drive inventory and metadata. 8 capabilities.
Read-only governance. 100% mature. Derived from W-GWS-API-001.

## 6. Google Docs API Package

W-GDOCS-API-001: Tab-aware document extraction. 9 capabilities.
Requires includeTabsContent=true, tabs traversal, childTabs recursion.
W0-001 coverage: 28 docs, 321 tabs, 134 child tabs, 283,831 words.
100% mature. Derived from W-GWS-API-001.

## 7. W-GWS-API-001 Reframe

W-GWS-API-001 preserved as provenance/backward-compatible alias.
Original code and tests unchanged. New packages reference it via
`legacy_provenance`. The monolithic path is now conceptually split
into Core + Drive API + Docs API.

## 8. W0-001 Package Set

Package set composes: Core + Drive API + Docs API + Drive CU + Docs CU.
- API slice: READY (Core, Drive API, Docs API all at 100%)
- CU slice: NOT READY (Drive CU 0%, Docs CU 0%)
- Full triple-test: NOT READY
- Memory activation: NOT READY (requires founder review)
- Future candidates (Gmail/Sheets/Slides/Calendar) excluded

## 9. Future Service Candidates

7 candidates: Gmail, Sheets, Slides, Calendar, Forms, Meet, Admin.
All FUTURE_CANDIDATE. None declared for W0-001. None block W0-001.
Each targets 100% when declared. Each requires own package + TME pack.

## 10. What Is Mature Now

- W-GWS-CORE-001 (shared foundation for W0-001)
- W-GDRIVE-API-001 (Drive inventory/metadata)
- W-GDOCS-API-001 (Docs tab-aware extraction)
- W-GWS-API-001 (legacy — preserved, still 100%)

## 11. What Is Not Mature

- W-GDRIVE-CU-001 (0% — CU infrastructure not proven)
- W-GDOCS-CU-001 (0% — CU infrastructure not proven)
- Gmail, Sheets, Slides, Calendar (not declared, future candidates)
- Operational tool adapter packages (not in scope of this phase)

## 12. What Still Blocks Full W0-001 Triple-Test

1. W-GDRIVE-CU-001 must reach 100%
2. W-GDOCS-CU-001 must reach 100%
3. Memory activation requires founder review

## 13. Recommended Next Gate

**BUILD_W_GDRIVE_CU_001_AND_W_GDOCS_CU_001_TO_100**

Alternative gates:
- RUN_W0_001_CU_HARDENING_TEST
- HARDEN_CU_DOCUMENT_READER_TO_100_PERCENT
- APPROVE_CU_VISIBLE_GOOGLE_DOCS_TEST
- VALIDATE_W0_001_DATA_INGESTION_AFTER_PACKAGE_SET_REFRAME
- PAUSE

## Deliverables

### Python Modules (10 new)

| Module | Purpose |
|--------|---------|
| adapter_family_contracts.py | Family/service/candidate contracts |
| package_set_contracts.py | Package set composition contracts |
| google_workspace_family.py | GWS family build with services/candidates |
| google_workspace_core_package.py | W-GWS-CORE-001 shared foundation |
| google_drive_api_package.py | W-GDRIVE-API-001 Drive API |
| google_docs_api_package.py | W-GDOCS-API-001 Docs API |
| google_drive_cu_package.py | W-GDRIVE-CU-001 Drive CU |
| google_docs_cu_package.py | W-GDOCS-CU-001 Docs CU |
| w0_001_package_set.py | W0-001 package set composition |
| google_workspace_service_candidates.py | Future service candidates |

### Test Files (10 new)

| File | Tests |
|------|-------|
| test_adapter_family_contracts.py | 12 |
| test_package_set_contracts.py | 17 |
| test_google_workspace_family.py | 21 |
| test_google_workspace_core_package.py | 17 |
| test_google_drive_api_package.py | 17 |
| test_google_docs_api_package.py | 23 |
| test_google_drive_cu_package.py | 17 |
| test_google_docs_cu_package.py | 20 |
| test_w0_001_package_set.py | 30 |
| test_google_workspace_service_candidates.py | 16 |

**Total new tests:** 190
**Prior tests (96.7A + 96.7B/C + W-GWS-API-001):** 263
**Total all tests:** 453+
**Regressions:** 0

### Doc Files (12 new)

| Doc | Location |
|-----|----------|
| Adapter Family Doctrine | docs/operations/adapter_family_doctrine_v1.md |
| GWS Adapter Family Doctrine | docs/operations/google_workspace_adapter_family_doctrine_v1.md |
| GWS Core Foundation | docs/operations/google_workspace_core_foundation_package_v1.md |
| Service Adapter Package Policy | docs/operations/google_service_adapter_package_policy_v1.md |
| W0-001 Package Set | docs/operations/w0_001_adapter_package_set_v1.md |
| Drive API Package | docs/operations/w_gdrive_api_001_adapter_package_v1.md |
| Docs API Package | docs/operations/w_gdocs_api_001_adapter_package_v1.md |
| Drive CU Package | docs/operations/w_gdrive_cu_001_adapter_package_v1.md |
| Docs CU Package | docs/operations/w_gdocs_cu_001_adapter_package_v1.md |
| W-GWS-API-001 Reframe | docs/system/w_gws_api_001_reframe_to_package_set_report.md |
| Post-Refactor Readiness | docs/system/w0_001_package_set_readiness_after_workspace_family_refactor.md |
| Phase 96.7D Report | docs/system/phase967d_google_workspace_adapter_family_refactor_report.md |

## Constraint Compliance

- No commit/push/memory promotion performed
- No private sources crawled
- No credentials captured
- No external tools installed
- No Playwright/CDP/screenshots used
- No CU marked as mature
- No full Google Workspace suite claimed mature
- No Gmail/Sheets/Slides/Calendar declared for W0-001
- W-GWS-API-001 preserved — not deleted
