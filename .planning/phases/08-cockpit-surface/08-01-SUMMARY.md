---
plan: 08-01
phase: 08-cockpit-surface
status: complete
started: 2026-05-30T01:15:00Z
completed: 2026-05-30T01:25:00Z
---

# Plan 08-01 Summary: Cockpit Template/Candidate/Governance Surface

## Result

6 new cockpit API routes added to cockpit_autonomous_routes.py for template registry, candidate supply, and governance visibility. Operator auth required on mutation endpoints.

## New Routes

| Route | Method | Auth | Purpose |
|---|---|---|---|
| /organism/template-registry | GET | none | Template audit summary with promoted/candidate/blocked counts |
| /organism/template-registry/promoted | GET | none | List all promoted templates with metadata |
| /organism/template-registry/candidates | GET | none | List recent candidate templates |
| /organism/candidate-supply | GET | none | Candidate supply engine summary (sources scanned) |
| /organism/candidate-supply/run | POST | operator | Execute candidate discovery scan |
| /organism/template-governance/evaluate | GET | none | Evaluate all promoted templates, show governance scores |

## Requirements Addressed

- **CKP-01:** template-registry + template-governance/evaluate surface promoted/candidate/blocked
- **CKP-02:** candidate-supply/run returns count, sources, best candidate, templates, policy
- **CKP-03:** cadence status endpoint already shows run history (pre-existing)
- **CKP-04:** candidate-supply/run requires operator token

## key-files

### modified
- transports/api/cockpit_autonomous_routes.py (333 → 451 lines)

## Deviations

None.

## Self-Check: PASSED
