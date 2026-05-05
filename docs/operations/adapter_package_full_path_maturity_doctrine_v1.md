# Adapter Package Full-Path Maturity Doctrine

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

For full Adapter Package maturity tests, every declared path must be
100% mature. A package is not mature if any declared path is partial,
blocked, unknown, not implemented, or requires approval.

## Example

A package with:
- API: COMPLETE
- Computer Use: PARTIAL
- MCP: UNKNOWN
- CLI direct: NOT_IMPLEMENTED

is **not** a fully mature Adapter Package if all four are declared paths.

## Declared Path Obligation

When a path is declared inside a package, the system accepts the
obligation to mature it to 100%. Declaring a path that stays at 0%
is worse than not declaring it — it creates a false maturity ceiling.

## Maturity Computation

Package maturity = (fully mature declared paths / total declared paths) * 100

Only declared paths count. Candidate paths are tracked separately.

## Full Adapter Test Gate

`can_use_for_full_adapter_test` is True only when:
- All declared paths are 100% mature
- No blocked declared paths
- No approval-required declared paths pending

## Module

`core/adapter_package_manager/full_path_maturity.py`
