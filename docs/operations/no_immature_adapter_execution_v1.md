# No Immature Adapter Execution

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

No immature Adapter Package or access path may execute. Partial paths
may only be used in explicit hardening/test mode.

## What "Immature" Means

An adapter package is immature if any of these are true:

- Missing adapter package
- Missing Tool Mastery Pack
- Stale Tool Mastery Pack
- Incomplete Tool Mastery Pack
- Missing auth profile
- Access path is PARTIAL, BLOCKED, NOT_IMPLEMENTED, or UNKNOWN
- Missing governance policy
- Missing no-secret policy
- Missing contract mapping
- Missing tests
- Known gaps affect the selected capability

## Hardening Mode Exception

Partial paths may be exercised in explicit hardening mode for the
purpose of maturing them to 100%. This is not production execution.

## Statuses That Block

| Status | can_execute |
|--------|-------------|
| MISSING_ADAPTER_PACKAGE | False |
| MISSING_TOOL_MASTERY_PACK | False |
| STALE_TOOL_MASTERY_PACK | False |
| INCOMPLETE_TOOL_MASTERY_PACK | False |
| MISSING_AUTH_PROFILE | False |
| ACCESS_PATH_PARTIAL | False |
| ACCESS_PATH_BLOCKED | False |
| ACCESS_PATH_NOT_IMPLEMENTED | False |
| ACCESS_PATH_UNKNOWN | False |
| MISSING_GOVERNANCE_POLICY | False |
| MISSING_NO_SECRET_POLICY | False |
| MISSING_CONTRACT_MAPPING | False |
| MISSING_TESTS | False |
| KNOWN_GAPS_AFFECT_EXECUTION | False |
| REQUIRES_APPROVAL | False |
| BLOCKED | False |
| EXECUTION_READY | True |
| WAIVED_BY_FOUNDER | True (controlled) |
