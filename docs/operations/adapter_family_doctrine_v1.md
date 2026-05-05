# Adapter Family Doctrine

**Version:** v1
**Date:** 2026-05-05

## Core Definitions

### Adapter Family

A suite-level grouping of related service adapter packages that share
auth, governance, identity, rate limits, and ecosystem-level mastery.

An Adapter Family is **NOT** a monolithic Adapter Package.

Example: Google Workspace Adapter Family.

### Core Foundation Package

Shared foundation package within a family. Contains shared
auth/session model, governance defaults, no-secret policy,
rate limit doctrine, and workspace-level Tool Mastery requirements.

Example: W-GWS-CORE-001.

### Service Adapter Package

Each product/service within a family gets its own Adapter Package
with its own maturity gate, governance policy, contract mapping,
tests, and Tool Mastery Pack.

Examples:
- W-GDRIVE-API-001 (Google Drive API)
- W-GDOCS-API-001 (Google Docs API)
- W-GDRIVE-CU-001 (Google Drive Computer Use)
- W-GDOCS-CU-001 (Google Docs Computer Use)

### Package Set

A composed operational bundle used for a specific test or workflow.
Selects packages from a family and evaluates readiness for the
specific test scope.

Example: W0-001 Package Set (Core + Drive API + Docs API + Drive CU + Docs CU).

## Why Not Monolithic

A monolithic "Google Workspace Adapter Package" would:
1. Conflate Drive maturity with Docs maturity
2. Make Gmail/Sheets/Slides block Drive/Docs tests
3. Hide service-specific gaps behind aggregate numbers
4. Prevent honest per-service maturity reporting
5. Force all services to share a single governance policy

## Hierarchy

```
Adapter Family (e.g., Google Workspace)
├── Core Foundation Package (shared auth/governance)
├── Service Package: Drive API
├── Service Package: Docs API
├── Service Package: Drive CU
├── Service Package: Docs CU
├── Future Candidate: Gmail
├── Future Candidate: Sheets
├── Future Candidate: Slides
├── Future Candidate: Calendar
└── Future Candidate: ...
```

## Rules

1. Each major product gets its own Adapter Package
2. Core Foundation handles shared concerns
3. Future candidates do not block current tests
4. Maturity is per-package, not per-family
5. A family is FULLY_MATURE only when all declared services are 100%

## Module

`core/adapter_package_manager/adapter_family_contracts.py`
