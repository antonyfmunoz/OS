# Stabilization H1: Post-Migration Hygiene Report

> Date: 2026-05-12
> Scope: Merge conflict triage, test baseline re-anchoring, relay verification scaffolding
> Constraint: No commits, no touches to runtime/core/services/eos_ai except as listed

---

## Executive Summary

H1 addressed three tracks of post-migration hygiene. All tracks complete.
Two items remain as proposals requiring manual approval (schema.ts resolution, archive deletion).

---

## Track 1: Merge Conflict Triage

### Finding: 9 reported conflicts → 2 actual

The ground truth audit flagged 9 files via `grep -rln "<<<<<<< "`. Investigation revealed
7 are **false positives** — they reference conflict markers in documentation, string literals,
or markdown backtick blocks. Only 2 files contain actual unresolved conflict markers.

| File | Verdict | Action |
|------|---------|--------|
| `saas/db/schema.ts` | ACTUAL CONFLICT | Proposal written (read-only per rules) |
| `archive/stale_backups/discord_bot.py.bak.20260508` | ACTUAL CONFLICT | Deletion proposed (archive rules) |
| `data/audits/2026-05-12_ground_truth_audit.md` | FALSE POSITIVE | References markers in documentation |
| `data/migration/r8b_validation_report.md` | FALSE POSITIVE | Mentions markers in report text |
| `data/migration/r8d_shim_generation_report.md` | FALSE POSITIVE | Mentions markers in report text |
| `data/migration/r8f_verification_report.md` | FALSE POSITIVE | Mentions markers in report text |
| `data/migration/post_r8h_stabilization_report.md` | FALSE POSITIVE | Mentions markers in report text |
| `docs/system/runtime_domain_architecture_plan.md` | FALSE POSITIVE | Mentions markers in plan text |
| `docs/system/phase968bh_codebase_truth_map.md` | FALSE POSITIVE | Mentions markers in truth map |

### Proposal: saas/db/schema.ts

Full analysis at: `data/proposals/schema_ts_conflict_resolution_proposal.md`

- Entire 978-line file is one conflict region
- Upstream (ours): 21 tables, 540 lines — superset
- Stashed (theirs): 17 tables, 435 lines — subset
- No migration references either side's unique tables
- **Recommendation**: Keep upstream. Resolution command provided in proposal.

### Proposal: archive/stale_backups/discord_bot.py.bak.20260508

- Zero live references anywhere in the repo
- Backup of pre-migration discord_bot.py (before runtime.* namespace)
- **Recommendation**: Delete. No downstream impact.

---

## Track 2: Test Baseline Re-Anchoring

### Finding: Claimed 8,684/2,691/495 → Actual 11,532/338

The handoff baseline (8,684 collected / 2,691 selected / 495 errors) does not match
current reality (11,532 collected / 338 collection errors). Root cause: baseline was
captured mid-migration or under different collection scope.

### Changes Made

**HISTORICAL reports (annotated, not modified):**

8 migration-era reports received an appended note clarifying the discrepancy:

1. `data/migration/r8b_validation_report.md`
2. `data/migration/r8c_validation_report.md`
3. `data/migration/r8d_validation_report.md`
4. `data/migration/r8e_validation_report.md`
5. `data/migration/r8f_validation_report.md`
6. `data/migration/r8g_validation_report.md`
7. `data/migration/r8h_equivalence_certification.md`
8. `data/migration/post_r8h_stabilization_report.md`

Annotation text:
```
[Note: Test baseline re-anchored 2026-05-12. Actual collection is 11,532 / 338 errors
(not 8,684 / 2,691 / 495 as stated at migration time). See ground truth audit.]
```

**LIVE document (updated):**

- `docs/system/runtime_domain_architecture_plan.md` line 506:
  Changed from `Test baseline holds (8684/2691/495)`
  to `Test baseline holds (11,532 collected / 338 collection errors — re-anchored 2026-05-12)`

---

## Track 3: Relay End-to-End Verification Scaffolding

### Deliverables

1. **Import smoke test**: PASSED
   ```
   from runtime.transport import windows_desktop_relay_client  # OK
   ```

2. **Verification script**: `scripts/verify_relay_end_to_end.sh` (chmod +x)
   - 5-step workflow: WSL detection → relay root resolution → heartbeat check → PING send → outbox poll
   - Exit 0 = PASS, 1 = FAIL
   - Writes proof artifact to `data/runtime/workstation_relay/proofs/`
   - Designed to run from WSL only (fails gracefully on VPS)

3. **Protocol document**: `docs/system/relay_e2e_verification_protocol.md`
   - Prerequisites, start commands, heartbeat behavior, PASS criteria
   - Common failure modes with causes and fixes
   - Proof artifact schema

### Not executed

The script was built but not run (VPS environment, no WSL). First execution
is for a WSL session with the Windows relay active.

---

## Files Changed (New)

| File | Type |
|------|------|
| `data/proposals/schema_ts_conflict_resolution_proposal.md` | NEW — proposal |
| `data/audits/2026-05-12_stabilization_h1_report.md` | NEW — this report |
| `scripts/verify_relay_end_to_end.sh` | NEW — executable script |
| `docs/system/relay_e2e_verification_protocol.md` | NEW — protocol doc |

## Files Changed (Modified)

| File | Change |
|------|--------|
| `data/migration/r8b_validation_report.md` | Appended baseline annotation |
| `data/migration/r8c_validation_report.md` | Appended baseline annotation |
| `data/migration/r8d_validation_report.md` | Appended baseline annotation |
| `data/migration/r8e_validation_report.md` | Appended baseline annotation |
| `data/migration/r8f_validation_report.md` | Appended baseline annotation |
| `data/migration/r8g_validation_report.md` | Appended baseline annotation |
| `data/migration/r8h_equivalence_certification.md` | Appended baseline annotation |
| `data/migration/post_r8h_stabilization_report.md` | Appended baseline annotation |
| `docs/system/runtime_domain_architecture_plan.md` | Line 506 baseline updated |

## Files NOT Changed (Proposals Only)

| File | Proposal |
|------|----------|
| `saas/db/schema.ts` | Keep upstream side — see proposal doc |
| `archive/stale_backups/discord_bot.py.bak.20260508` | Delete — zero references |

---

## Open Items

1. **schema.ts**: Awaiting approval to resolve conflict (keep upstream)
2. **discord_bot.py.bak**: Awaiting approval to delete from archive
3. **Relay E2E**: Script ready, first run blocked until WSL session with active Windows relay
4. **Shim monitoring**: 14-day window active (2026-05-12 → 2026-05-26), daily cron running

---

## Deliverable Checklist

- [x] Conflict triage: all 9 files classified (7 false positive, 2 actual)
- [x] schema.ts proposal: `data/proposals/schema_ts_conflict_resolution_proposal.md`
- [x] archive deletion proposal: documented in this report
- [x] Test baseline: 8 reports annotated + 1 live doc updated
- [x] Relay script: `scripts/verify_relay_end_to_end.sh` (executable)
- [x] Relay protocol: `docs/system/relay_e2e_verification_protocol.md`
- [x] H1 report: this file
