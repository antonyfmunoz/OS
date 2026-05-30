# Roadmap: Phase 10.0 — Production Template Library + Cadence Candidate Supply + Cockpit Quality Gate

## Overview

Phase 10.0 transforms the autonomous cadence from "alive but empty" into a governed continuous-improvement radar. Starting from a verified PR #44 merge, it extracts cockpit.py below the 3000-line quality gate, audits and seeds a production template library backed by real phase outcomes, installs a 9-dimension governance scoring engine, builds a candidate supply engine fed by real system observations, integrates everything into cadence dry-run, surfaces template and candidate state in the cockpit, generates a PR factory preview, verifies the cockpit through authenticated browser testing, closes the phase with 80+ new tests, and produces a full audit report. Every artifact traces to evidence. No production mutation ever occurs.

## Phases

- [ ] **Phase 1: Preflight** - Merge PR #44, lock foundation, verify cadence mode and production truth post-merge
- [ ] **Phase 2: Cockpit Quality Gate** - Extract cockpit.py route groups, bring file under 3000 lines, preserve all API contracts
- [ ] **Phase 3: Template Audit** - Classify all existing templates, identify gaps and missing categories
- [ ] **Phase 4: Template Seeding** - Seed evidence-backed templates from Phase 9.2-9.9 outcomes, 10+ categories
- [ ] **Phase 5: Template Governance** - 9-dimension scoring engine, cadence eligibility decisions, blocking rules
- [ ] **Phase 6: Candidate Supply Engine** - Discover candidates from real sources, rank by confidence, block unsafe
- [ ] **Phase 7: Cadence Integration** - Wire real supply into dry-run, persist results, prove > 0 candidates or truthful empty
- [ ] **Phase 8: Cockpit Surface** - Display template audit summary, candidate supply state, dry-run history
- [ ] **Phase 9: PR Factory Preview** - Preview mode review packet from top eligible candidate, no actual PR
- [ ] **Phase 10: Browser Verification** - Authenticated smoke test or exact auth blocker documentation
- [ ] **Phase 11: Testing** - 80+ new tests covering all new production code, prior suites passing, pre-commit gates
- [ ] **Phase 12: Audit Report** - Full phase 10.0 audit with all verification evidence

## Phase Details

### Phase 1: Preflight
**Goal**: Foundation is locked — PR #44 merged, runtime matches main, cadence confirmed dry_run_only, production truth endpoints verified operational
**Depends on**: Nothing (first phase)
**Requirements**: PRE-01, PRE-02, PRE-03, PRE-04
**Success Criteria** (what must be TRUE):
  1. PR #44 is merged to main and git log shows the merge commit
  2. `git rev-parse HEAD` on VPS runtime matches main HEAD
  3. Cadence scheduler reports dry_run_only mode when queried
  4. All four production truth endpoints return valid responses post-merge
**Plans**: 2 plans
Plans:
- [x] 01-01-PLAN.md — Confirm PR #44 merge and classify changed files, document HEAD alignment
- [x] 01-02-PLAN.md — Verify cadence mode dry_run_only + all 4 production truth endpoints + write preflight audit

### Phase 2: Cockpit Quality Gate
**Goal**: cockpit.py is below 3000 lines and all API contracts (paths, response shapes, auth, WebSocket) are fully preserved after route extraction
**Depends on**: Phase 1
**Requirements**: CQG-01, CQG-02, CQG-03, CQG-04, CQG-05, CQG-06
**Success Criteria** (what must be TRUE):
  1. `wc -l cockpit.py` reports fewer than 3000 lines
  2. Every previously-existing API path is still reachable at the same URL
  3. Operator token gates on extracted routes reject unauthenticated requests identically to before
  4. WebSocket handshake and message flow behave identically after extraction
  5. Zero endpoints were removed — count before equals count after
**Plans**: 3 plans
Plans:
- [ ] 02-01-PLAN.md — Extract organism core routes (30 handlers) into cockpit_organism_routes.py
- [ ] 02-02-PLAN.md — Extract entity/product routes (9 handlers) into cockpit_entity_routes.py
- [ ] 02-03-PLAN.md — Extract economy/topology + autonomous PR factory + cadence routes (38 handlers) into cockpit_economy_routes.py + cockpit_autonomous_routes.py; verify final line count < 3000
**UI hint**: yes

### Phase 3: Template Audit
**Goal**: Every existing template is classified with one of eight labels, missing categories are identified, and candidate discovery gaps are documented
**Depends on**: Phase 2
**Requirements**: TPL-01, TPL-02
**Success Criteria** (what must be TRUE):
  1. Audit report lists every existing template file with its classification label
  2. All eight classification labels (production_ready, candidate_ready, needs_evidence, missing_validation, missing_rollback, unsafe_risk, stale, duplicate) appear or are documented as not present
  3. At least one "missing template category" gap is identified and documented
  4. Audit output is persisted and cockpit-visible
**Plans**: TBD

### Phase 4: Template Seeding
**Goal**: At least 10 evidence-backed template categories exist in the library, each with full metadata, defaulting to candidate status, with no template promoted without validation and rollback proof
**Depends on**: Phase 3
**Requirements**: TPL-03, TPL-04, TPL-05, TPL-06, TPL-07
**Success Criteria** (what must be TRUE):
  1. Template library contains entries in at least 10 distinct categories (observation_path_fix through docs_audit_update)
  2. Every seeded template includes all required fields: template_id, name, type, action_type, trigger/applicability/contraindication conditions, steps, validation_strategy, rollback_strategy, risk_class, required_capabilities, confidence, evidence_ids, source_phase
  3. Templates without validated evidence or rollback proof remain in candidate status, not production_ready
  4. Every seeded template's evidence_ids reference actual ProductionOutcomeCommitted records or Phase 9.2-9.9 artifacts
**Plans**: TBD

### Phase 5: Template Governance
**Goal**: A governance scoring engine evaluates every template on 9 dimensions and produces a cadence_eligible, candidate_only, operator_review_required, or blocked decision with reason codes
**Depends on**: Phase 4
**Requirements**: GOV-01, GOV-02, GOV-03, GOV-04, GOV-05
**Success Criteria** (what must be TRUE):
  1. TemplateGovernanceScore produces scores for all 9 dimensions (evidence, validation, rollback, risk, reliability, specificity, reversibility, blast_radius, agent_capability)
  2. A LOW-risk template with evidence >= 0.70, validation >= 0.80, rollback >= 0.70 receives cadence_eligible decision
  3. A template referencing sensitive paths, keywords, or auth/credential/DNS/container mutation receives blocked decision
  4. Every non-passing decision includes at least one reason code
  5. Templates that fail only on operator_review thresholds receive operator_review_required, not blocked
**Plans**: TBD

### Phase 6: Candidate Supply Engine
**Goal**: CandidateSupplyEngine discovers real candidates from all registered sources, each with evidence and policy decision, ranked by confidence, unsafe candidates blocked
**Depends on**: Phase 5
**Requirements**: CSE-01, CSE-02, CSE-03, CSE-04, CSE-05
**Success Criteria** (what must be TRUE):
  1. CandidateSupplyEngine can be invoked and returns candidates from at least one real source type (ContradictionEngine, WorldModel, DependencyGraph, ReadinessModel, BottleneckEngine, cockpit truth matrix, route/API mismatch, template audit, test failures, or line count gate)
  2. Every returned candidate includes all required fields: candidate_id, source, title, description, evidence, affected_files, risk_class, matching_templates, policy_decision, blocked_reasons, expected_delta, recommended_next_step
  3. No candidate is returned with an empty evidence field
  4. Candidates are ranked — highest template confidence and agent reliability appear first
  5. Candidates with unsafe risk class or sensitive paths appear only in the blocked list with reason codes, not in the actionable list
**Plans**: TBD

### Phase 7: Cadence Integration
**Goal**: Cadence dry-run uses real CandidateSupplyEngine output, produces > 0 candidates or a truthful empty explanation with source scan proof, persists results, and creates no mutations
**Depends on**: Phase 6
**Requirements**: CAD-01, CAD-02, CAD-03, CAD-04, CAD-05
**Success Criteria** (what must be TRUE):
  1. Cadence dry-run log references CandidateSupplyEngine, not a hardcoded candidate list
  2. Dry-run result shows at least one candidate OR includes a source-scan proof explaining why each source returned zero
  3. Every candidate in dry-run output has an evidence field and a policy_decision
  4. No PR is created and no file is modified as a result of running dry-run
  5. Dry-run results appear in persisted storage and are queryable via cockpit API
**Plans**: TBD

### Phase 8: Cockpit Surface
**Goal**: Cockpit displays template library status, candidate supply state, and dry-run history — all mutation controls require operator token
**Depends on**: Phase 7
**Requirements**: CKP-01, CKP-02, CKP-03, CKP-04
**Success Criteria** (what must be TRUE):
  1. Cockpit /template-registry endpoint returns audit summary, promoted count, candidate count, and blocked count
  2. Cockpit /candidate-supply endpoint returns total count, source breakdown, best candidate title, matching template, and policy decision
  3. Cockpit /cadence endpoint returns dry-run history entries and next scheduled dry-run timestamp
  4. Any POST/PATCH to template or candidate endpoints without a valid operator token returns 401
**Plans**: TBD
**UI hint**: yes

### Phase 9: PR Factory Preview
**Goal**: The top eligible candidate can produce a full review packet in preview mode — no actual PR is created
**Depends on**: Phase 8
**Requirements**: PRF-01, PRF-02, PRF-03
**Success Criteria** (what must be TRUE):
  1. Invoking PR factory preview on the top eligible candidate completes without creating a GitHub PR
  2. Preview output includes: candidate evidence, matched template name, policy decision, proposed diff or change description
  3. Preview result is persisted and accessible via cockpit API
**Plans**: TBD

### Phase 10: Browser Verification
**Goal**: Cockpit is verified through authenticated browser testing OR the exact auth blocker is documented with steps to reproduce
**Depends on**: Phase 9
**Requirements**: BRW-01, BRW-02, BRW-03
**Success Criteria** (what must be TRUE):
  1. Either a Playwright smoke test completes with all major cockpit panels loading, OR an exact error trace is documented showing where Clerk-authenticated flow blocks automated testing
  2. Build hash in cockpit matches the deployed commit hash (if testable)
  3. Template registry and candidate supply panels are visible in cockpit (verified by test screenshot or documented blocker)
**Plans**: TBD
**UI hint**: yes

### Phase 11: Testing
**Goal**: All new production code has tests, all prior phase suites pass, pre-commit gates pass, and the minimum 80 new tests threshold is met
**Depends on**: Phase 10
**Requirements**: TST-01, TST-02, TST-03, TST-04, TST-05, TST-06, TST-07, TST-08
**Success Criteria** (what must be TRUE):
  1. `pytest` reports at least 80 new test functions added during Phase 10.0
  2. TemplateSeeder, TemplateGovernance, CandidateSupplyEngine, and cadence integration test suites all pass
  3. Route extraction tests confirm all routes are importable, routers are mounted, auth is preserved, and response shapes are unchanged
  4. All pre-commit gates (type divergence, instance leak, dependency direction, projection boundary) pass with zero violations
  5. All prior phase test suites (Phases 8 through 9.9) continue to pass
**Plans**: TBD

### Phase 12: Audit Report
**Goal**: A complete Phase 10.0 audit report exists documenting all work, verification evidence, and any remaining blockers
**Depends on**: Phase 11
**Requirements**: AUD-01, AUD-02
**Success Criteria** (what must be TRUE):
  1. Audit report file exists at data/audits/2026-05-29_phase_10_0_audit.md
  2. Report contains sections for: preflight, template audit findings, seeded library summary, governance scoring evidence, candidate supply proof, cadence dry-run proof, route extraction proof with line count before/after, browser verification result or blocker, PR factory preview output, test results, and remaining blockers
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Preflight | 0/2 | Planning complete | - |
| 2. Cockpit Quality Gate | 0/3 | Planning complete | - |
| 3. Template Audit | 0/TBD | Not started | - |
| 4. Template Seeding | 0/TBD | Not started | - |
| 5. Template Governance | 0/TBD | Not started | - |
| 6. Candidate Supply Engine | 0/TBD | Not started | - |
| 7. Cadence Integration | 0/TBD | Not started | - |
| 8. Cockpit Surface | 0/TBD | Not started | - |
| 9. PR Factory Preview | 0/TBD | Not started | - |
| 10. Browser Verification | 0/TBD | Not started | - |
| 11. Testing | 0/TBD | Not started | - |
| 12. Audit Report | 0/TBD | Not started | - |
