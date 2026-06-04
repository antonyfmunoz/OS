# UMH Open Questions -- Operator Decision Queue

**Phase:** 14.6B-UMH (revised 14.6F) | **Status:** PARTIALLY RESOLVED | **Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

These questions cannot be resolved from code or documentation alone. They require operator judgment. Q1-Q5 have been resolved via operator ratification in Phase 14.6C/14.6E. Q6-Q15 remain open for future phases.

**Resolved:** 5 of 15 | **Open:** 10 of 15

---

## Naming

**Q1.** ~~Confirm that "Universal Meta Harness" is the canonical product name.~~
- **STATUS: RESOLVED** (DEC-146B-UMH-001, ratified 2026-06-04, Phase 14.6E)
- **Ratified answer:** "Universal Meta Harness" is the canonical product name. "Universal Mastery Hierarchy" is stale.
- Impact: ~50 files need renaming, README rewrite, PHILOSOPHY.md rewrite

**Q2.** ~~Should PHILOSOPHY.md be rewritten to use UMH instead of EntrepreneurOS?~~
- **STATUS: RESOLVED** (DEC-146B-UMH-002, ratified 2026-06-04, Phase 14.6E)
- **Ratified answer:** Rewrite PHILOSOPHY.md to be UMH-universal, not EOS-specific (Option A).
- Impact: Foundational document that defines system values

## Architecture

**Q3.** ~~Three parallel execution paths exist. What is the target?~~
- **STATUS: RESOLVED** (DEC-146B-UMH-003, ratified 2026-06-04, Phase 14.6E)
- **Ratified answer:** Unify into single execution path (Substrate -> SignalRouter -> Spine) (Option A).
- Impact: Governance, memory, and tracing differ across paths

**Q4.** ~~Should substrate/execution/workers/workstation/ (26,671 lines, 43 files) be deleted?~~
- **STATUS: RESOLVED** (DEC-146B-UMH-004, ratified 2026-06-04, Phase 14.6E)
- **Ratified answer:** Extract conceptual value into design docs, then delete dead workstation code.
- Risk: May contain conceptual value worth preserving elsewhere

**Q5.** ~~ProductConnectionManager imports from projections/ (upward dependency). How should this be resolved?~~
- **STATUS: RESOLVED** (DEC-146B-UMH-005, ratified 2026-06-04, Phase 14.6E)
- **Ratified answer:** Abstract port pattern via substrate/sockets/projection_port.py (Option B).

## Cockpit

**Q6.** What is the minimum Cockpit MVP -- which panels and capabilities must work before any implementation phase begins?
- All 27 panels exist but some back-end connections are stubs
- 7 execution control endpoints are stubs
- Need operator to define the minimum viable command center

**Q7.** Should each projection have its own cockpit panel section, or should projection visibility be unified?
- Currently: EOS has dedicated endpoints (/eos/pipeline, /eos/kpis, /eos/activity)
- CreatorOS and LyfeOS have no dedicated cockpit views
- Options: Per-projection sections vs unified cross-projection view

## Security

**Q8.** Should dev bypass be removed before any production deployment?
- Currently: UMH_DEV_BYPASS=true allows unauthenticated access from private IPs
- Acceptable for single-operator VPS behind Tailscale
- Must be disabled for any multi-user scenario
- Recommended: Keep for now, add to P1 hardening

**Q9.** Should substrate database connection switch from neondb_owner (BYPASSRLS) to a restricted role?
- Currently: All RLS policies bypassed for Python substrate code
- Risk: Low in single-operator phase, critical if multi-tenant
- Recommended: Create substrate-specific role for P1 hardening

## Data Boundaries

**Q10.** What LyfeOS data should be explicitly excluded from UMH ingestion?
- Therapy session content, trauma narratives, self-harm indicators, medication details
- These categories need explicit signal emitter filtering
- Operator must define the exclusion list

**Q11.** Should cross-projection data sharing be opt-in per projection or globally configured?
- Example: Should CreatorOS analytics be available to EOS marketing workflows?
- Example: Should LyfeOS energy levels inform EOS scheduling?
- Recommended: Opt-in per projection pair with operator approval

## Execution

**Q12.** What is the maximum autonomy level for overnight/unattended operation?
- Current: Dry-run only (no production changes without operator approval)
- Should organism be able to execute LOW-risk actions autonomously overnight?
- Recommended: Keep dry-run-only until cockpit readiness is verified

**Q13.** Should the simulation dry-run and deliberation council be mandatory for all HIGH/CRITICAL actions, or configurable per action type?
- Currently: Both run for all HIGH/CRITICAL signals
- Some HIGH actions may not benefit from simulation (e.g., reading external APIs)
- Recommended: Configurable via governance policy

## Infrastructure

**Q14.** VPS is a single point of failure. What is the disaster recovery strategy?
- Currently: No backup/restore tested for Neon database
- No runbook for service recovery
- Recommended: P1 -- create backup verification + recovery runbook

**Q15.** Should Docker health checks be added before next deployment?
- Currently: No health checks in docker-compose.yml
- Services could fail silently
- Recommended: P1 -- add health checks to all services
