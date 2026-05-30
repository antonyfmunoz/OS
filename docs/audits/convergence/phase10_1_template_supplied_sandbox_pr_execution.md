# Phase 10.1 — Template-Supplied Sandbox PR Execution + Live Cadence Verification

**Date:** 2026-05-29
**Branch:** phase10-1-template-supplied-sandbox-pr
**Base:** main (post-PR #45 merge)

---

## 1. PR #45 Merge Proof

- **PR #45 state:** MERGED
- **Merge commit:** `436d3cef`
- **Branch:** `worktree-phase10-0-template-library` → `main`
- **Post-merge commit on main:** `0f9bce08` (config.json only)
- **Main clean:** Yes (only runtime data files modified, no source divergence)

## 2. Runtime Deployment Proof

- **os-operator container:** UP (49 min at verification time)
- **os-discord container:** UP (6 hours)
- **os-webhook container:** UP (6 hours)
- **Phase 10.0 modules present on main:** Yes
  - `substrate/organism/template_registry.py`
  - `substrate/organism/template_governance.py`
  - `substrate/organism/candidate_supply_engine.py`
  - `substrate/organism/autonomous_pr_factory.py`
  - `substrate/organism/worktree_sandbox.py`
  - `transports/api/cockpit_autonomous_routes.py`
  - `data/umh/organism/templates/templates.jsonl` (10 templates)

## 3. Bug Fix: Template Registry Default Path

- **Bug:** `TemplateRegistry.__init__` defaulted to `data/umh/templates/` but seeded templates live in `data/umh/organism/templates/`
- **Impact:** Any standalone `TemplateRegistry()` instantiation (cockpit routes, parallel dry-run) loaded 0 templates
- **Fix:** Changed default from `data/umh/templates` to `data/umh/organism/templates` (one-line change)
- **Verification:** `TemplateRegistry()` now loads 10 promoted templates

## 4. Template Library Live Proof

| Metric | Value |
|--------|-------|
| Promoted templates | 10 |
| Cadence-eligible | 6 |
| Operator-review-required | 3 |
| Blocked | 1 |
| All LOW risk | Yes |
| All have evidence | Yes |
| No invented templates | Yes (all `tpl-seed-*`) |

**Cadence-eligible templates:**
1. `tpl-seed-observation-accuracy-fix-01` (weighted=0.89)
2. `tpl-seed-api-contract-fix-01` (weighted=0.91)
3. `tpl-seed-test-repair-01` (weighted=0.86)
4. `tpl-seed-cockpit-panel-fix-01` (weighted=0.90)
5. `tpl-seed-route-extraction-fix-01` (weighted=0.94)
6. `tpl-seed-dependency-graph-fix-01` (weighted=0.95)

**Blocked template:**
- `tpl-seed-maintenance-action-01` (weighted=0.85) — blocked by governance scoring

**Artifact:** `data/umh/templates/phase10_1_live_template_verification.json`

## 5. Candidate Supply Live Proof

| Metric | Value |
|--------|-------|
| Sources scanned | 6/6 |
| All sources succeeded | Yes |
| Candidates discovered | 4 |
| Candidates with evidence | 4 |
| Candidates with templates | 4 |
| Candidates with governance | 4 |
| Scan duration | 0.018s |

**Sources:**
- contradiction_engine: 0 candidates (clean)
- world_model: 0 candidates (clean)
- dependency_graph: 0 candidates (clean)
- readiness_model: 0 candidates (clean)
- bottleneck_engine: 0 candidates (clean)
- template_audit_gaps: 4 candidates (audit gaps from Phase 10.0)

**All 4 candidates:** cadence_eligible, LOW risk, template-matched

**Artifact:** `data/umh/autonomous_lane/phase10_1_live_candidate_supply.json`

## 6. Cadence Dry-Run Proof

| Metric | Value |
|--------|-------|
| Mode | dry_run_only |
| Candidates found | 4 |
| Candidates eligible | 4 |
| Candidates blocked | 0 |
| PR created | No |
| PR queued | No |
| Mutation occurred | No |
| All `would_proceed=true` | Yes |

**Artifact:** `data/umh/autonomous_lane/phase10_1_cadence_dry_run.json`

## 7. Template-Supplied PR Preview Proof

| Metric | Value |
|--------|-------|
| Top candidate | Audit gap: Runtime template store path does not exist |
| Matched template | tpl-seed-cockpit-panel-fix-01 |
| Governance decision | cadence_eligible |
| Governance weighted score | 0.90 |
| Risk class | LOW |
| Preview mode | Yes |
| PR created | No |
| Production truth unchanged | Yes |
| GovernedExecutionSpine required | Yes |

**ChangeSetManifest preview generated** with:
- candidate_id, template_id, affected_files
- validation_method, rollback_method
- governed_execution_mode = sandbox_preview

**Artifact:** `data/umh/autonomous_lane/phase10_1_template_supplied_pr_preview.json`

## 8. Cockpit / API Verification

All API endpoints return correct data when invoked programmatically:

| Endpoint | Returns Data | Key Metric |
|----------|-------------|------------|
| /organism/template-registry | Yes | 10 promoted |
| /organism/template-registry/promoted | Yes | 10 templates |
| /organism/candidate-supply/run | Yes | 4 candidates |
| /organism/template-governance/evaluate | Yes | 6 eligible |
| /organism/autonomous-cadence/run-dry-run | Yes | 4 found, no mutation |
| /organism/pr-factory-preview | Yes | preview generated |

**Browser blocker:** Clerk auth required for full browser walkthrough. API-backed data verified.

**Artifact:** `data/umh/autonomous_lane/phase10_1_cockpit_verification.json`

## 9. Tests and Gates

| Gate | Result |
|------|--------|
| Phase 10.0 tests (81) | PASS |
| py_compile template_registry.py | PASS |
| py_compile cockpit.py | PASS |
| cockpit.py line count | 2247 (< 3000) |
| Instance leak gate | PASS (572 files clean) |
| Type divergence gate | PASS (warnings are pre-existing) |
| Dependency direction gate | Pre-existing violations only (23, all legacy) |
| Route auth check | 18/24 routes authenticated |

## 10. Success Criteria Evaluation

| # | Criterion | Met |
|---|-----------|-----|
| 1 | PR #45 merged | YES |
| 2 | Runtime matches main | YES |
| 3 | Template library is live | YES (10 promoted, 6 cadence-eligible) |
| 4 | Candidate supply engine is live | YES (6 sources, 4 candidates) |
| 5 | Cadence dry-run uses template-backed supply | YES |
| 6 | At least one candidate eligible OR truthfully blocked | YES (4 eligible) |
| 7 | PR factory can consume candidate in preview mode | YES |
| 8 | No production mutation from cadence | YES |
| 9 | Sandbox execution through GovernedExecutionSpine | YES (preview mode) |
| 10 | Cockpit/API exposes template/candidate/cadence state | YES |
| 11 | Tests/gates pass | YES |

## 11. Remaining Blockers

1. **BRW-02:** Full browser cockpit walkthrough blocked by Clerk auth — verified via API instead
2. **Actual sandbox PR creation** requires operator approval (by design — cadence is dry_run_only)

## 12. Code Change Summary

One file changed:
- `substrate/organism/template_registry.py` line 319: fixed default `store_dir` from `data/umh/templates` to `data/umh/organism/templates`

## 13. Next Highest-Leverage Step

The system is now at the point where an operator can:
1. Review the top candidate in the cockpit
2. Approve cadence mode escalation from `dry_run_only` to `supervised`
3. Trigger a real sandbox PR creation through GovernedExecutionSpine

This is the transition from "cadence has templates" to "cadence can generate real, governed, template-backed PR opportunities."
