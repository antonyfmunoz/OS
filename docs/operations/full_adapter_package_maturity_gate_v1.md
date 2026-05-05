# Full Adapter Package Maturity Gate

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

The full maturity gate evaluates every declared path, not just the
selected path. This is the gate used for Adapter Package certification.

## When to Use

- Before certifying an Adapter Package for production
- During W0-001 or similar package validation tests
- When evaluating whether a tool is fully integrated into UMH

## Evaluation

For each declared path, check 7 maturity dimensions:
1. Current status is COMPLETE
2. Tool Mastery Pack exists and is mature
3. Auth method defined
4. Governance policy defined
5. Tests present
6. Contract mapping present
7. No known gaps

## Package-Level Decision

| Condition | Result |
|-----------|--------|
| All declared paths 100% mature | FULLY_MATURE |
| Any declared path partial | HAS_PARTIAL_DECLARED_PATHS |
| Any declared path blocked | HAS_BLOCKED_DECLARED_PATHS |
| Any declared path unknown | HAS_UNKNOWN_DECLARED_PATHS |
| Any declared path not implemented | HAS_NOT_IMPLEMENTED_DECLARED_PATHS |
| Any declared path requires approval | HAS_REQUIRES_APPROVAL_DECLARED_PATHS |
| Path marked complete but has gaps | INVALID_FAKE_COMPLETE |

## Fake Complete Detection

A path that claims COMPLETE status but has known gaps, missing mastery,
or missing tests is rejected as INVALID_FAKE_COMPLETE.

## Module

`core/adapter_package_manager/full_path_maturity.py`
