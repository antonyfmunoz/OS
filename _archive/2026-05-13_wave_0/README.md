# Wave 0 Archive — 2026-05-13

Migration Wave 0: scaffold and unreachable files removed from active tree.

These files are preserved on disk and in git history. They are no longer
in the active development tree. Recovery: `git mv` back from this directory.

## Source

- Plan: `/opt/OS/data/audits/2026-05-13_triage_manifest.md`
- Audits consumed: exploration, core spot, salience, gap analysis (all 2026-05-13)

## What's here

| Category | Files | Source | Reason |
|----------|-------|--------|--------|
| Core scaffold | ~288 | `core/` (26 subdirs) | 0 external callers, 0 commits, AI-generated scaffold |
| Scaffold tests | 26 | `tests/test_*_v1.py` | Tests that only test archived scaffold |
| Transport orphans | 149 | `runtime/transport/` | 0 external callers outside transport/ |
| Legacy tests | 423 | `tests/legacy/` | Pre-migration tests for prior architecture |
| Phase reports | 96 | `docs/system/phase968*` | Superseded planning docs |
| Dormant services | 3 | `services/` | Not running, 0 imports |
| Frontend stub | 3 | `frontend/` | Minimal stub, no development |
| Orchestrator | 7 | `orchestrator/` | Markdown-only, no Python |

## Recovery

```bash
git mv _archive/2026-05-13_wave_0/<path> <original_path>
```
