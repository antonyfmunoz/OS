# Google Service Adapter Package Policy

**Version:** v1
**Date:** 2026-05-05

## Core Policy

Each major Google product gets its own Adapter Package.

Google Workspace is a family/suite, not a single adapter.
Service adapter packages inherit from the Core Foundation Package
but have their own:
- Capability maps
- Governance policies
- Contract mappings
- Tool Mastery Packs
- Tests
- Maturity gates
- Hardening plans

## Current Service Packages

| Package ID | Service | Type | Maturity |
|-----------|---------|------|----------|
| W-GDRIVE-API-001 | Google Drive | API | 100% |
| W-GDOCS-API-001 | Google Docs | API | 100% |
| W-GDRIVE-CU-001 | Google Drive | CU | 0% |
| W-GDOCS-CU-001 | Google Docs | CU | 0% |

## Future Service Packages

When declared in the future, each requires:
1. Its own Adapter Package (capability map, governance, contract)
2. Its own Tool Mastery Pack
3. Its own test suite
4. Its own maturity gate
5. Inheritance from W-GWS-CORE-001 for shared concerns

## Naming Convention

`W-G{SERVICE}-{TYPE}-{VERSION}`

Examples:
- W-GDRIVE-API-001
- W-GDOCS-CU-001
- W-GMAIL-001
- W-GSHEETS-001
