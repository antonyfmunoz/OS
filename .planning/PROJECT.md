# Phase 10.0 — Production Template Library + Cadence Candidate Supply + Cockpit Quality Gate

## What This Is

UMH Phase 10.0 transforms the dry-run autonomous cadence from "alive but empty" into a useful continuous improvement radar. It builds a governed template library, candidate supply engine, and cockpit quality improvements so the system continuously surfaces evidence-backed, template-matched, low-risk improvements for operator-governed execution.

## Core Value

UMH can maintain a governed library of low-risk production templates, feed scheduled cadence with real candidate supply, keep the cockpit quality gate clean, and verify the cockpit through authenticated browser testing.

## Requirements

### Validated

- Phase 9.8 deployed and production truth active
- Phase 9.9 verified: runtime matches main, ProductionMergeVerifier works, ProductionTruthDelta works, ProductionOutcomeCommitted works, scheduled cadence active in dry_run_only mode, cockpit loads publicly, PR #44 created

### Active

- [ ] PR #44 merged and verified (preflight)
- [ ] Template library audit completed with classification
- [ ] Evidence-backed low-risk templates seeded from prior phase outcomes
- [ ] Template governance scoring system with cadence eligibility
- [ ] Candidate supply engine fed by real system observations
- [ ] Cadence dry-run produces real candidates (or truthful empty explanation)
- [ ] cockpit.py extracted below 3000-line quality gate
- [ ] Authenticated browser smoke test or documented blocker
- [ ] Cockpit surfaces template and candidate supply state
- [ ] Template-supplied sandbox PR preview generated
- [ ] 80+ new tests covering all new production code
- [ ] Audit report documenting all phase work

### Out of Scope

- Full autonomy / auto-merge — cadence remains non-mutating
- Auth/credential/DNS changes — no security surface modifications
- Broad refactors beyond cockpit route extraction
- Fake template/candidate/browser data — everything must trace to evidence
- UI redesign — incremental cockpit surface updates only

## Context

Phase 9.9 proved the autonomous cadence infrastructure works but returns 0 candidates because production template supply is too thin. The cadence execution pipeline is:
Candidate -> Template match -> Policy evaluation -> Dry-run -> Sandbox PR factory -> Operator merge -> Production verification -> ProductionOutcomeCommitted.

The bottleneck is template supply. Without templates, cadence sees nothing. Without governance, templates could propose unsafe work.

Current issues:
- cockpit.py is 3542 lines (above 3000-line quality gate)
- Browser smoke test blocked by Clerk-authenticated flow
- Cadence is operational but not useful as a proposal engine

## Constraints

- **No mutation**: Cadence must remain dry_run_only — no production changes without operator approval
- **Evidence-backed**: Every template must trace to a proven prior phase outcome
- **Risk-gated**: Only LOW risk templates are cadence-eligible
- **Quality gate**: cockpit.py must be under 3000 lines
- **Docker**: Python 3.11 only — no 3.12+ syntax
- **Architecture**: substrate/ never imports from transports/ or services/
- **Type coherence**: No parallel types — check canonical_types.py first

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Skip research phase | Domain is deeply known from 9 prior phases | -- Pending |
| Fine granularity (12 subphases) | Mission spec defines 12 discrete deliverables (10.0A-10.0L) | -- Pending |
| No auto-merge ever | Cadence proposes, operator decides | -- Pending |
| Route extraction for cockpit quality | cockpit.py at 3542 lines blocks quality gate | -- Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check -- still the right priority?
3. Audit Out of Scope -- reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-29 after initialization*
