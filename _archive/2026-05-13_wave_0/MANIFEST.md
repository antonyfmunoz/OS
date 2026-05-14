# Wave 0 Archive Manifest

## Summary

| Category | Files | Status |
|----------|-------|--------|
| Core scaffold (26 dirs) | 288 | Archived |
| Scaffold tests | 26 | Archived |
| Legacy tests | 423 | Archived |
| Phase reports (docs/system/phase968*) | 96 | Archived |
| Dormant services | 3 | Archived |
| Frontend stub | 3 | Archived |
| Orchestrator (markdown) | 7 | Archived |
| Transport orphans (149 files) | 0 | DEFERRED |
| **Total** | **849** (846 + README + MANIFEST) | |

## Deferred: Transport Orphans

149 transport modules could not be archived in Wave 0.
Reason: `runtime/transport/__init__.py` hard-imports 26 of the 30
"orphan" modules, and the kept modules have internal cross-imports
to 13 more. The transport layer's `__init__.py` acts as a massive
re-export surface, making piecemeal archival impossible without
code modification (which Wave 0 prohibits).

Resolution: Archive transport orphans in a dedicated wave where
`__init__.py` is rewritten to lazy-import or remove the re-exports.

## Detailed Listings

### Core Scaffold (26 subdirectories, 288 .py files)

Directories archived:
- `core/accountability/` (14 files)
- `core/applications/` (12 files)
- `core/certification/` (13 files)
- `core/cognition/` (11 files)
- `core/constitutional/` (13 files)
- `core/convergence/` (15 files)
- `core/deployment/` (12 files)
- `core/environments/` (12 files)
- `core/explainability/` (13 files)
- `core/federation/` (13 files)
- `core/ingress/` (10 files)
- `core/intelligence/` (14 files)
- `core/knowledge/` (14 files)
- `core/learning/` (11 files)
- `core/operations/` (12 files)
- `core/orchestration/` (12 files)
- `core/planning/` (1 files)
- `core/resilience/` (12 files)
- `core/scaling/` (12 files)
- `core/sessions/` (10 files)
- `core/stabilization/` (12 files)
- `core/trust/` (13 files)
- `core/validation/` (14 files)
- `core/workflows/` (9 files)
- `core/world_model/` (4 files)

### Scaffold Tests (26 files)

Tests that only import archived scaffold modules. Never part of migration test suite.

### Legacy Tests (423 files)

`tests/legacy/` — pre-migration tests for prior architectural iterations.

### Phase Reports (96 files)

`docs/system/phase968*` — superseded planning documents from phase 96.8 series.

### Dormant Services (3 files)

- `services/dm_monitor.py` — Instagram DM monitor (not running)
- `services/telegram_control.py` — Telegram bot (service disabled)
- `services/apify_scraper.py` — Instagram scraper (not running)

### Frontend Stub (3 files)

Minimal web UI stub with no development activity.

### Orchestrator (7 markdown files)

Markdown-only orchestrator directory. No Python code.
