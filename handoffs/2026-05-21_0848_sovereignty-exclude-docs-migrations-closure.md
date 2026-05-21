# Handoff — 2026-05-21 Sovereignty Exclude docs/migrations/ Closure

## Status: COMPLETE

Follows: `2026-05-21_0750_test-debt-closure.md`

Locks sovereignty grep baseline to 20 by structurally excluding
`docs/migrations/` — migration plans that by definition document
old→new identifier renames. Bundles a pre-existing script/doc
sync orphan fix.

## What Changed

**Branch commit**: `323f7199` on `sovereignty-exclude-docs-migrations`
**Merge commit**: `4c05668d` on `main` (--no-ff)
**Push**: `d9532237..4c05668d` to `origin/main`
**Scope**: 2 files changed, 8 insertions

### Files modified

| File | Change |
|------|--------|
| `scripts/sovereignty-grep.sh` | +1 pipe line: `grep -v '/docs/migrations/'` |
| `10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md` | +1 section "Migration Planning Documents" with `docs/migrations/` rationale; +1 row `data/codebase_graph.json` in "Auto-Generated Indices" (orphan fix) |

### Calibration note

Previous baseline of 20 was an undercount. The `docs/migrations/` hit
was always present but below the grep's effective scan window prior to
the Q2-Q6 wiki doc placement (commit `b94c0e27`). Audit-undercount
law applies recursively to the audit tool itself. Corrected baseline:
20 (after exclusion).

### Sovereignty grep final output (20 hits, all DATA)

```
understanding/knowledge/knowledge_integrator.py:85     — 'hormozi_youtube' example in docstring
data/system/runtime_domain_module_map.json:28           — martell_patterns.py module listing
data/audits/2026-05-14_exhaustive_system_audit.md:283   — Dan Martell mention in audit
data/audits/2026-05-14_runtime_layer_classification.md  — 5 hits (martell_patterns rows)
data/drive_doc_ingestion_tab_aware/Antony_F._Munoz_*    — Dan Martell in personal brand doc
data/drive_doc_ingestion_tab_aware/Coaching_Philosophy_* — "Buy Back Time" in coaching doc
skills/tools/apify/references/best_practices.md         — 2 hits (hormozi scraper example)
skills/tools/instagram/references/best_practices.md     — hormozi competitor example
10_Wiki/SOVEREIGNTY_GREP_EXCLUSIONS.md:62               — self-referential (hormozi_content example)
.planning/codebase/INTEGRATIONS.md:92                   — hormozi competitor target
09_Content/Content_Ideas/content_ideas_2026_03_16.md:61 — "perfect week" in content idea
docs/audits/phase12_eos_liquidation_report.md:64        — buyback_rate/drip_matrix/perfect_week in report
docs/audits/file_classification_table.md:396            — martell_patterns.py classification
docs/audits/essentialism_audit.md                       — 2 hits (martell_patterns in file lists)
```

## Deferred Items

### NEW
- **Dead EXCLUDES array** in `sovereignty-grep.sh` (lines 17-49) — ripgrep-style `--glob` entries never referenced by `run_grep()`. Decision needed: remove (cleanest) vs wire up (if there's intent behind the array structure). Small scope, sibling to script/doc sync work.

### UPDATED
- **Sovereignty baseline**: locked at 20 via structural exclusion.
- **17 pre-existing test failures**: resolved in prior handoff (`2026-05-21_0750`). 0 failures.

### UNCHANGED
- Layer 3 Phase 1 implementation (heavyweight, fresh session)
- Discord command identifiers (`!buyback`, `!drip`, `!perfectweek`) — UX decision
- Graph pruning verify — PASS (confirmed in test-debt session)
- eos_ai/ status — confirmed dead (0 imports, untracked), safe to delete
- Snapshot-graph tarball script (low priority)

## What's NOT Next

No auto-prioritized queue. Next session picks priority.
