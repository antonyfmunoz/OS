# Phase 14.0 — Trinity Convergence Plan

**Date:** 2026-05-31
**Phase:** 14.0 — Projection Source Reconciliation + Product Projection Kernel
**Status:** Plan created. Awaiting operator permission for external source inspection.

## Executive Summary

Phase 14.0 has completed local source discovery. The source universe for UMH's projection ecosystem (EOS, CreatorOS, LyfeOS) spans 5 known locations: VPS /opt/OS (production truth for UMH), /opt/OS/saas (partial EOS backend), Windows Beast /dev (likely full Trinity apps), GitHub (committed source), and Google Docs (documentation). Three of these are uninspected pending operator permission.

## Discovered Divergences

| # | Type | Projection | Severity | Requires Permission |
|---|------|------------|----------|-------------------|
| 1 | Uninspected source (Google Docs) | SharedTrinity | HIGH | Yes |
| 2 | Uninspected source (GitHub) | SharedTrinity | HIGH | Yes |
| 3 | Uninspected source (Beast /dev) | SharedTrinity | HIGH | Yes |
| 4 | Partial backend | EOS | HIGH | Yes |
| 5 | Schema version split (v1 vs v2) | EOS | HIGH | No |
| 6 | Code duplication (integration layer) | SharedTrinity | MEDIUM | No |
| 7 | Schema drift (7 migration-only tables) | EOS | MEDIUM | No |
| 8 | Type inconsistency (text vs uuid FKs) | EOS | MEDIUM | No |
| 9 | Instance context in seed data | EOS | LOW | No |

## Permission Requests

1. **Windows Beast /dev** — read-only SSH access to inspect Trinity app directories
2. **GitHub** — read-only access to list repos, branches, and source trees
3. **Google Docs** — read-only access to inspect projection documentation
4. **Device discovery** — read-only /dev listing for additional artifacts

## Convergence Sequence

1. Local discovery (COMPLETE)
2. Permission acquisition (PENDING)
3. Source inspection (Windows Beast → GitHub → Google Docs)
4. Cross-source comparison
5. Canonicality decisions (operator only)
6. Convergence execution plan
7. Work Packet execution (Phase 14.1+)

## Key Findings

- **/opt/OS/saas is partial** — 12 API routes, 13 DB tables, no frontend, no auth, significant CRUD gaps
- **EOS has a schema version split** — saas uses v2 (events/clients/ventures), integration uses v1 (crm_*)
- **CreatorOS and LyfeOS are integration stubs** — 8 files each, no application-layer code
- **Integration layer is copy-pasted** across all 3 projections — candidate for shared base
- **7 tables exist in migrations but not in schema.ts** — schema drift
- **Seed data is instance-specific** — not parametrized

## No-Destructive-Sync Guarantee

Phase 14.0 performs zero writes to external systems. All data is local to `/opt/OS/data/umh/projection_reconciliation/`. No source is auto-canonized.

## Evidence

- Convergence plan: `data/umh/projection_reconciliation/trinity_convergence_plan.json`
- Divergence diagnostic: `data/umh/projection_reconciliation/phase14_0_divergence_diagnostic.json`
- Source map: `data/umh/projection_reconciliation/projection_source_map.json`
- Permission requests: `data/umh/projection_reconciliation/phase14_0_permission_requests.json`
