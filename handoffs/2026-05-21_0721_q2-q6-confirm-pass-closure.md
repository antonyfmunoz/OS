# Handoff — 2026-05-21 Q2-Q6 Confirm Pass + Architecture Doc Promotion

## Status: COMPLETE

Follows: `2026-05-21_0559_q1-codebase-pages-closure.md`

Closes the remaining 5 of 6 Layer 3 architecture questions as far-phase
direction confirms, and promotes the architecture doc to canonical wiki.

## What Changed

**Merge commit**: `b94c0e27` on `main` (q2-q6-confirm-pass)
**Feature commit**: `9bab2717`
**Scope**: 2 files changed, 658 insertions

## Resolutions

| Q | Resolution | Phase |
|---|---|---|
| Q1 | Codebase pages → data/codebase_pages/ (gitignored) | DONE — `ebcf068b` |
| Q2 | Notion stays EXTERNAL; socket wiring is legacy convenience | Phase 2 |
| Q3 | browser-use through model_router.call_with_fallback() | Phase 4 |
| Q4 | SCHEMA layer formalization | Phase 6 |
| Q5 | Cross-device / Tailscale diagnostic | Phase 4 |
| Q6 | Trust deterministic hashing for dedup | Phase 6 |

## Architecture Doc Promotion

- Source: `/tmp/layer3_unified_architecture.md` (deleted)
- Target: `/opt/OS/10_Wiki/LAYER_3_UNIFIED_ARCHITECTURE.md`
- YAML frontmatter added with promotion metadata
- Status line changed from DRAFT to CANONICAL
- Section 10 rewritten from "Open Questions" to "Architecture Questions (All RESOLVED)"
- Cross-linked from `10_Wiki/LAYER_3.1_SOVEREIGNTY_CLEANUP.md` via `successor:` field

## Verification

- Sovereignty grep: 21 hits (pre-existing +1 from docs/migrations/ scan window,
  0 from the new architecture doc)
- New doc has zero external-name violations
- /tmp source confirmed deleted
- Code gates N/A (docs-only merge)

## Deferred Queue (Updated)

**DONE this session:**
- 6 architecture questions (Q1-Q6)
- Architecture doc merge/promotion
- Archive-hygiene (Bucket D) — prior merge
- Test-hygiene (4 broken classes) — prior merge
- Import-os collection error — prior merge

**Still deferred:**
- Layer 3 Phase 1 implementation (Modality + ParticipantType + AdapterManifest
  as first-class types — heavyweight, fresh-session initiative)
- 17 pre-existing test failures (triage with pytest --collect-only per file first)
- Discord command identifiers (!buyback, !drip, !perfectweek — UX decision)
- Graph pruning verify (post-Q1 regen should be clean)
- eos_ai/ status (delete vs keep dormant)
- Snapshot-graph tarball script (low priority)

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
