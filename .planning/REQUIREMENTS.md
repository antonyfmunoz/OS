# Requirements: Phase 10.0 — Production Template Library + Cadence Candidate Supply

**Defined:** 2026-05-29
**Core Value:** UMH continuously identifies evidence-backed, template-matched, low-risk improvements for operator-governed execution

## v1 Requirements

### Preflight

- [ ] **PRE-01**: PR #44 merged to main and verified
- [ ] **PRE-02**: Runtime commit matches main HEAD after merge
- [ ] **PRE-03**: Cadence mode confirmed dry_run_only post-merge
- [ ] **PRE-04**: Production truth endpoints verified operational post-merge

### Cockpit Quality

- [x] **CQG-01**: cockpit.py route groups extracted into dedicated route modules
- [x] **CQG-02**: cockpit.py under 3000 lines after extraction
- [x] **CQG-03**: All extracted routes preserve API paths and response shapes
- [x] **CQG-04**: All extracted routes preserve auth/operator token requirements
- [x] **CQG-05**: WebSocket behavior preserved after extraction
- [x] **CQG-06**: No endpoint removal during extraction

### Template Library

- [ ] **TPL-01**: Template audit classifies all existing templates (production_ready, candidate_ready, needs_evidence, missing_validation, missing_rollback, unsafe_risk, stale, duplicate)
- [ ] **TPL-02**: Template audit identifies missing template categories and candidate discovery gaps
- [ ] **TPL-03**: Evidence-backed templates seeded from Phase 9.2-9.9 outcomes and ProductionOutcomeCommitted records
- [ ] **TPL-04**: Each seeded template includes template_id, name, type, action_type, trigger/applicability/contraindication conditions, steps, validation_strategy, rollback_strategy, risk_class, required_capabilities, confidence, evidence_ids, source_phase
- [ ] **TPL-05**: All seeded templates default to candidate status unless evidence threshold met
- [ ] **TPL-06**: No template promoted without validation and rollback/non-mutating proof
- [ ] **TPL-07**: Minimum 10 template categories seeded (observation_path_fix through docs_audit_update)

### Template Governance

- [ ] **GOV-01**: TemplateGovernanceScore evaluates 9 dimensions (evidence, validation, rollback, risk, reliability, specificity, reversibility, blast_radius, agent_capability)
- [ ] **GOV-02**: Governance produces cadence_eligible, candidate_only, operator_review_required, or blocked decisions
- [ ] **GOV-03**: Cadence eligibility requires LOW risk, evidence >= 0.70, validation >= 0.80, rollback >= 0.70 OR non_mutating, reliability >= 0.70
- [ ] **GOV-04**: Governance blocks templates with sensitive paths, sensitive keywords, broad file patterns, or auth/credential/DNS/container mutation
- [ ] **GOV-05**: Every governance rejection includes reason codes

### Candidate Supply

- [ ] **CSE-01**: CandidateSupplyEngine discovers candidates from ContradictionEngine, WorldModel gaps, DependencyGraph issues, ReadinessModel weaknesses, BottleneckEngine, cockpit truth matrix, route/API mismatches, template audit gaps, test failures, line count gates
- [ ] **CSE-02**: Each candidate includes candidate_id, source, title, description, evidence, affected_files, risk_class, matching_templates, policy_decision, blocked_reasons, expected_delta, recommended_next_step
- [ ] **CSE-03**: No candidate created without evidence
- [ ] **CSE-04**: Candidates ranked by template confidence and agent reliability
- [ ] **CSE-05**: Unsafe candidates blocked with reasons

### Cadence Integration

- [ ] **CAD-01**: Cadence dry-run uses real candidate supply (not hardcoded)
- [ ] **CAD-02**: Cadence discovers > 0 candidates OR truthfully explains why zero with source scan proof
- [ ] **CAD-03**: Every discovered candidate has evidence and policy decision
- [ ] **CAD-04**: No PR created and no mutation during dry-run
- [ ] **CAD-05**: Dry-run results persisted and cockpit-visible

### Cockpit Surface

- [ ] **CKP-01**: Cockpit displays template audit summary, promoted/candidate/blocked templates
- [ ] **CKP-02**: Cockpit displays candidate supply count, source breakdown, best candidate, matching template, policy decision
- [ ] **CKP-03**: Cockpit displays dry-run history and next scheduled dry-run
- [ ] **CKP-04**: Template/candidate mutation controls require operator token

### PR Factory Preview

- [ ] **PRF-01**: Top eligible candidate can feed PR factory in preview mode
- [ ] **PRF-02**: Review packet generated without creating actual PR
- [ ] **PRF-03**: Preview shows candidate evidence, template match, policy decision

### Browser Verification

- [ ] **BRW-01**: Authenticated browser smoke test completed OR exact auth blocker documented
- [ ] **BRW-02**: If testable: all major cockpit panels load, build hash matches, WebSocket connected, no console errors
- [ ] **BRW-03**: Template registry and candidate supply visible in cockpit

### Testing

- [ ] **TST-01**: TemplateSeeder tests (evidence loading, candidate creation, risk assignment, validation/rollback requirements)
- [ ] **TST-02**: TemplateGovernance tests (eligibility pass, risk blocking, evidence blocking, validation blocking, rollback blocking, sensitive path blocking, reason codes)
- [ ] **TST-03**: CandidateSupplyEngine tests (builds from each source type, template matching, ranking, unsafe blocking, serialization)
- [ ] **TST-04**: Cadence integration tests (dry-run uses supply, no mutation, persists candidates, truthful empty supply)
- [ ] **TST-05**: Route extraction tests (routes imported, routers mounted, auth preserved, response shapes unchanged)
- [ ] **TST-06**: All prior phase test suites pass (8 through 9.9)
- [ ] **TST-07**: Pre-commit gates pass (type divergence, instance leak, dependency direction, projection boundary)
- [ ] **TST-08**: Minimum 80 new tests for new production code

### Audit

- [ ] **AUD-01**: Phase 10.0 audit report created with all verification evidence
- [ ] **AUD-02**: Report includes preflight, template audit, seeded library, governance, candidate supply, cadence proof, route extraction proof, cockpit line count before/after, browser proof or blocker, PR preview, test results, remaining blockers

## v2 Requirements

### Autonomous Execution

- **AEX-01**: Cadence transitions from dry_run_only to operator-approved execution mode
- **AEX-02**: Automated sandbox PR creation from cadence-eligible candidates
- **AEX-03**: Operator approval workflow in cockpit for cadence-proposed PRs

### Template Evolution

- **TEV-01**: Templates update confidence scores based on execution outcomes
- **TEV-02**: Template version history with diff tracking
- **TEV-03**: Community template sharing across UMH instances

## Out of Scope

| Feature | Reason |
|---------|--------|
| Auto-merge | Cadence must remain non-mutating in Phase 10.0 |
| Full autonomous execution | Supply chain must be proven before execution unlocked |
| Auth/credential changes | No security surface modifications in this phase |
| UI redesign | Incremental cockpit surface updates only |
| Fake/synthetic data | Every template and candidate must trace to real evidence |
| Broad refactors | Only cockpit route extraction is in scope |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PRE-01 | Phase 1 | Pending |
| PRE-02 | Phase 1 | Pending |
| PRE-03 | Phase 1 | Pending |
| PRE-04 | Phase 1 | Pending |
| CQG-01 | Phase 2 | Complete |
| CQG-02 | Phase 2 | Complete |
| CQG-03 | Phase 2 | Complete |
| CQG-04 | Phase 2 | Complete |
| CQG-05 | Phase 2 | Complete |
| CQG-06 | Phase 2 | Complete |
| TPL-01 | Phase 3 | Pending |
| TPL-02 | Phase 3 | Pending |
| TPL-03 | Phase 4 | Pending |
| TPL-04 | Phase 4 | Pending |
| TPL-05 | Phase 4 | Pending |
| TPL-06 | Phase 4 | Pending |
| TPL-07 | Phase 4 | Pending |
| GOV-01 | Phase 5 | Pending |
| GOV-02 | Phase 5 | Pending |
| GOV-03 | Phase 5 | Pending |
| GOV-04 | Phase 5 | Pending |
| GOV-05 | Phase 5 | Pending |
| CSE-01 | Phase 6 | Pending |
| CSE-02 | Phase 6 | Pending |
| CSE-03 | Phase 6 | Pending |
| CSE-04 | Phase 6 | Pending |
| CSE-05 | Phase 6 | Pending |
| CAD-01 | Phase 7 | Pending |
| CAD-02 | Phase 7 | Pending |
| CAD-03 | Phase 7 | Pending |
| CAD-04 | Phase 7 | Pending |
| CAD-05 | Phase 7 | Pending |
| CKP-01 | Phase 8 | Pending |
| CKP-02 | Phase 8 | Pending |
| CKP-03 | Phase 8 | Pending |
| CKP-04 | Phase 8 | Pending |
| PRF-01 | Phase 9 | Pending |
| PRF-02 | Phase 9 | Pending |
| PRF-03 | Phase 9 | Pending |
| BRW-01 | Phase 10 | Pending |
| BRW-02 | Phase 10 | Pending |
| BRW-03 | Phase 10 | Pending |
| TST-01 | Phase 11 | Pending |
| TST-02 | Phase 11 | Pending |
| TST-03 | Phase 11 | Pending |
| TST-04 | Phase 11 | Pending |
| TST-05 | Phase 11 | Pending |
| TST-06 | Phase 11 | Pending |
| TST-07 | Phase 11 | Pending |
| TST-08 | Phase 11 | Pending |
| AUD-01 | Phase 12 | Pending |
| AUD-02 | Phase 12 | Pending |

**Coverage:**
- v1 requirements: 48 total
- Mapped to phases: 48
- Unmapped: 0

---
*Requirements defined: 2026-05-29*
*Last updated: 2026-05-29 after initial definition*
