# Declared Path vs Candidate Path Policy

**Version:** 1.0
**Date:** 2026-05-05
**Scope:** UMH substrate — all platform consumers

## Core Rule

Future candidates may exist in backlog/discovery, but they do not count
as mature package paths. To declare a path inside a package, the system
accepts the obligation to mature it to 100%.

## Declared Path

- Part of the package's maturity obligation
- Must mature to 100%
- Blocks full package maturity if not complete
- Appears in maturity score denominator
- Can execute only when 100% mature

## Future Candidate

- Known possible path
- Tracked in backlog/discovery
- Does not count as mature package path
- Cannot be used for execution
- Cannot be represented as part of a 100% mature package
- Does not appear in maturity score denominator

## Blocked/Requires-Approval Path

- Can be tracked
- Cannot count as mature
- Creates approval/hardening work order
- Blocks full package maturity until resolved

## Declaration Statuses

| Status | Counts Toward Maturity | Can Execute |
|--------|----------------------|-------------|
| DECLARED | Yes (when 100%) | Yes (when 100%) |
| FUTURE_CANDIDATE | No | No |
| BLOCKED_DEPENDENCY | No | No |
| REQUIRES_APPROVAL | No (until approved + validated) | No |
| DEPRECATED | No | No |
| EXCLUDED_FROM_PACKAGE | No | No |

## Anti-Pattern

Declaring a path as DECLARED when it is actually a future candidate
inflates the maturity obligation and creates false reporting. Paths
should only be declared when there is active intent to mature them.
