---
plan: 09-01
phase: 09-pr-factory-preview
status: complete
started: 2026-05-30T01:25:00Z
completed: 2026-05-30T01:35:00Z
---

# Plan 09-01 Summary: PR Factory Preview Endpoint

## Result

GET /organism/pr-factory-preview endpoint added. Discovers top candidate via CandidateSupplyEngine, matches template, evaluates governance, and returns a preview review packet. No actual PR is created.

## New Routes

| Route | Method | Auth | Purpose |
|---|---|---|---|
| /organism/pr-factory-preview | GET | none | Generate preview review packet from top eligible candidate |

## Preview Packet Contents

- candidate: full candidate details (id, source, title, evidence, risk, templates, policy)
- template_match: matched template with steps, validation, rollback
- governance: 9-dimension governance score and decision
- policy_decision: cadence_eligible/blocked/etc
- would_create_pr: boolean based on policy decision
- pr_created: always false (preview mode)
- source_scan_proof: evidence that all sources were scanned

## Requirements Addressed

- **PRF-01:** Top candidate feeds PR factory preview
- **PRF-02:** Review packet generated without creating actual PR
- **PRF-03:** Preview shows candidate evidence, template match, policy decision

## key-files

### modified
- transports/api/cockpit_autonomous_routes.py (451 → 508 lines)

## Deviations

None.

## Self-Check: PASSED
