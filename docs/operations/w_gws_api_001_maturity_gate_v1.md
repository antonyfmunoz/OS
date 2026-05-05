# W-GWS-API-001 Maturity Gate

**Version:** v1
**Date:** 2026-05-05
**Path ID:** W-GWS-API-001

## Purpose

10-check maturity gate that determines whether the API tab-aware
adapter path is 100% mature and execution-ready.

## Maturity Checks (10)

| # | Check Name | What It Validates |
|---|-----------|-------------------|
| 1 | path_exists | Adapter path W-GWS-API-001 builds successfully |
| 2 | path_declared | Declaration status is DECLARED |
| 3 | current_status_complete | Current status is "complete" |
| 4 | has_auth_method | Auth method is defined and opaque |
| 5 | governance_policy_passes | Read-only + blocks mutation + blocks credential capture |
| 6 | contract_mapping_passes | Requires includeTabsContent + tabs traversal + childTabs recursion |
| 7 | tool_mastery_pack_present | TME pack is present and referenced |
| 8 | tests_present | Test suite exists |
| 9 | first_tab_only_rejected | First-tab-only extraction is not allowed |
| 10 | w0_001_coverage_contract | W0-001 coverage contract is represented |

## Maturity Calculation

- **Current maturity %** = (passed checks / total checks) × 100
- **100% mature** = all 10 checks pass
- **Execution ready** = all 10 checks pass
- **Gaps** = list of check names that did not pass

## Decision Dataclass

`W_GWS_API_001_MaturityDecision` contains:
- path_id
- checks (list of W_GWS_API_001_MaturityCheck)
- all_passed
- current_maturity_percent
- target_maturity_percent (always 100.0)
- is_100_percent_mature
- is_execution_ready
- gaps_to_100

## Full GWS Package Behavior

`google_workspace_package_is_fully_mature_with_cu_partial()` always
returns False because:
- API path (W-GWS-API-001) is DECLARED and complete → 100%
- CU path (W-GWS-CU-001) is DECLARED but partial → NOT 100%
- Full package requires ALL declared paths at 100%

This is correct and intentional — it proves that per-path maturity
does not equal package maturity.

## Convenience Functions

| Function | Returns |
|----------|---------|
| w_gws_api_001_is_100_percent_mature() | bool — True when all 10 pass |
| build_w_gws_api_001_maturity_decision() | Full decision object |
| build_w_gws_api_001_gap_report() | Dict with path_id, is_100_percent, gaps, checks |

## Module

`core/adapter_package_manager/google_workspace_api_maturity.py`
