# UMH Open Questions -- Operator Decision Queue

**Phase:** 14.6B-UMH | **Status:** DRAFT | **Provenance:** OPEN_QUESTION_OPERATOR_DECISION_REQUIRED

These questions cannot be resolved from code or documentation alone. They require operator judgment.

---

## Naming

**Q1.** Confirm that "Universal Meta Harness" is the canonical product name. The pyproject.toml uses universal-meta-harness, README says Universal Mastery Hierarchy. Which is correct?
- Recommended: Universal Meta Harness (per this phase's operator correction)
- Impact: ~50 files need renaming, README rewrite, PHILOSOPHY.md rewrite

**Q2.** Should PHILOSOPHY.md be rewritten to use UMH instead of EntrepreneurOS, or should it remain as the EOS-specific philosophy with a separate UMH philosophy document?
- Option A: Rewrite PHILOSOPHY.md to be UMH-universal
- Option B: Keep PHILOSOPHY.md as EOS philosophy, create UMH_PHILOSOPHY.md
- Impact: Foundational document that defines system values

## Architecture

**Q3.** Three parallel execution paths exist. What is the target?
- Option A: Unify into single path (Path 2: Substrate -> SignalRouter -> Spine)
- Option B: Keep Path 1 for conversational, Path 2 for programmatic, Path 3 for batch
- Option C: Keep Path 1 as production, deprecate others
- Impact: Governance, memory, and tracing differ across paths

**Q4.** Should substrate/execution/workers/workstation/ (26,671 lines, 43 files) be deleted?
- Identified as dead code in exhaustive audit
- Constitutional engines with no callers
- Risk: May contain conceptual value worth preserving elsewhere
- Recommended: Archive, then delete from substrate/

**Q5.** ProductConnectionManager imports from projections/ (upward dependency). How should this be resolved?
- Option A: Move to projections/ or transports/ layer
- Option B: Use abstract registration pattern via substrate/sockets/projection_port.py
- Option C: Accept as a pragmatic exception with documentation
- Recommended: Option B (abstract port pattern)

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
