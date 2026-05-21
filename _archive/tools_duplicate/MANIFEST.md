# tools/ Duplicate Archive Manifest

Archived during convergence Wave 1 — 2026-05-10.

## Why Archived

`tools/` was a stale fork of `scripts/`. Both directories contained
near-identical Python files with diverging edits over time.
`scripts/` is the canonical operations directory.

## File Disposition

- 140+ files existed in both tools/ and scripts/ (all DIFFER — diverged copies)
- 1 file was EXACT duplicate (__init__.py)
- 23 files existed ONLY in tools/ — all classified dead/duplicated:
  - 4 dead test files (test_adaptive_orchestration, test_builder_delivery,
    test_plan_executor, test_session_rhythm)
  - 1 dead smoke test (session_watcher_concurrency_smoke_test)
  - 3 dead standalone scripts (validate_stabilized_complete, cc_reply_webhook,
    run_pipeline_trace)
  - 8 duplicated in services/ (local_bridge_client/server, cost_tracker,
    overnight_scrape, icp_scorer, heartbeat, apify_scraper, kpi_tracker)
  - 7 dead duplicate parsers_lib/ (duplicate of root parsers/)

## Import Safety

- Zero external importers found outside tools/
- Only internal importer: umh/interfaces/discord/bot.py (dormant, scheduled Wave 2)
- No live service imports from tools/
- No core/ imports from tools/
- No eos_ai/ imports from tools/

## Note on parsers/

Root-level parsers/ was NOT archived — it has live importers in
scripts/codebase_graph.py, scripts/incremental_graph.py,
and scripts/verify_knowledge_system.py.

## Rollback

```bash
git revert <wave-1-commit>
```
