---
plan: 05-01
phase: 05-template-governance
status: complete
started: 2026-05-30T00:30:00Z
completed: 2026-05-30T00:45:00Z
---

# Plan 05-01 Summary: Template Governance Scoring Engine

## Result

substrate/organism/template_governance.py written (267 lines, py_compile clean). 9-dimension scoring engine evaluates templates and produces cadence_eligible, candidate_only, operator_review_required, or blocked decisions with reason codes.

## Key Findings

- **module:** substrate/organism/template_governance.py (267 lines)
- **dimensions:** 9 (evidence, validation, rollback, risk, reliability, specificity, reversibility, blast_radius, agent_capability)
- **decision_types:** 4 (cadence_eligible, candidate_only, operator_review_required, blocked)
- **blocking_rules:** sensitive paths, sensitive keywords, broad file patterns, mutation keywords
- **cadence_thresholds:** evidence >= 0.70, validation >= 0.80, rollback >= 0.70, reliability >= 0.70
- **operator_review_thresholds:** evidence >= 0.50, validation >= 0.60, rollback >= 0.50, reliability >= 0.50

## Evaluation Against 10 Seeded Templates

| Template | Decision | Weighted Score | Key Reason |
|---|---|---|---|
| contradiction-fix | operator_review_required | 0.92 | validation 0.70 < 0.80 threshold |
| readiness-improvement | operator_review_required | 0.88 | validation 0.70 < 0.80 threshold |
| observation-accuracy-fix | cadence_eligible | 0.89 | all thresholds met |
| world-model-accuracy-fix | operator_review_required | 0.90 | validation 0.70 < 0.80 threshold |
| api-contract-fix | cadence_eligible | 0.91 | all thresholds met |
| test-repair | cadence_eligible | 0.86 | all thresholds met |
| cockpit-panel-fix | cadence_eligible | 0.90 | all thresholds met |
| route-extraction-fix | cadence_eligible | 0.94 | all thresholds met |
| dependency-graph-fix | cadence_eligible | 0.95 | all thresholds met |
| maintenance-action | blocked | 0.85 | mutation_keyword:container |

## Blocking Rules Verified

- Sensitive path (.env) → BLOCKED
- Credential keywords (api_key, secret) → BLOCKED
- Mutation keywords (container) → BLOCKED
- All blocked decisions include reason codes

## Requirements Addressed

- **GOV-01:** 9 dimension scoring implemented
- **GOV-02:** 4 decision types produced
- **GOV-03:** Cadence eligibility thresholds enforced (LOW risk, evidence >= 0.70, validation >= 0.80, rollback >= 0.70, reliability >= 0.70)
- **GOV-04:** Blocking rules for sensitive paths, keywords, broad patterns, mutation keywords
- **GOV-05:** Every non-eligible decision includes reason codes

## key-files

### created
- substrate/organism/template_governance.py

## Deviations

None.

## Self-Check: PASSED
