---
type: codewiki-dir
dir: logs
---

# `logs/` — operational log tree: signals, decisions, execution traces, cron output

**212,532 files · ~346 MB · [Full file inventory](../inventory/logs.md)**

*(Counts as of the manifest's `generated_at` 2026-07-10T20:18Z, git SHA `a5f09e48e`. `logs/` is a rollup of live, append-only operational output — it drifts constantly and is the single largest file-count directory in the repo after the worktree/git internals.)*

## Purpose
`logs/` is where every long-running loop, daemon, and script drops its operational output: cron job logs (`morning_*.log`, `nightly_*.log`), error streams (`errors.jsonl`, `model_router_errors.jsonl`, `discord_bot_errors.jsonl`), the event spine (`event_spine.jsonl`), and structured subsystem trees under subdirectories. It is entirely gitignored (`.gitignore` line 47, `logs/`) — nothing here is source, all of it is runtime exhaust. `data/logs` is a symlink into this tree, so the two names address the same files.

## How it fits
`logs/` is written by every layer — `substrate/` (signals, idempotency, decisions), `transports/`, `services/` daemons, and `scripts/` cron loops — and read almost never by code (it is the last resort in the retrieval hierarchy: *Palace → Graph → Summaries → Raw Source → Logs / Transcripts*). Only humans and debugging agents `grep` it. It imports nothing and is imported by nothing; it is a pure sink.

## Structure
Nine structured subdirectories plus ~150 loose top-level log files. The subdir file counts (measured with `find`, as of this page):

| Subdir | Files | Role · producer |
|---|---|---|
| `signals/` | 211,126 | One dir per signal name, each with `pending/` and `processed/`. Written by `substrate/control_plane/runtime/orchestrator/signals.py::emit_signal` (`SIGNALS_ROOT = {root}/logs/signals`) and `scripts/emit_signal.py`. **This one subtree is >99% of the directory's file count.** |
| `tool_mastery_research/` | 1,045 | TME research artifacts. Producer: `scripts/tool_mastery_research_dispatcher.py`, `substrate/composition/mastery/research/*` |
| `idempotency/` | 92 | Action idempotency keys. Producer: `substrate/control_plane/actions/idempotency.py` |
| `decisions/` | 77 | Recorded decisions. Producer: `scripts/decisions.py`, `substrate/control_plane/actions/logging.py` |
| `execution/` | 55 | Execution-loop traces |
| `deferred/` | 13 | Deferred-work records |
| `archive/` | 4 | Rotated/archived logs (rotation destination) |
| `exports/` | 2 | Exported log bundles |
| `relay_queue/` | 1 | Vision/mesh relay queue |

Loose top-level files include daily `morning_YYYYMMDD.log` / `nightly_YYYYMMDD.log` (one per day, back to 2026-05-15), health logs (`cc_auth_health.log`, `cc_session_health.log`, `cpu_watchdog.log`), JSONL streams (`event_spine.jsonl`, `harness_event_log.jsonl`, `pipeline_trace.jsonl`, `workstation.jsonl` + `.1`), and Instagram debug screenshots (`ig_*.png`).

## Key components
- `logs/signals/` — the signal bus on disk. `emit_signal(name, payload)` writes a JSON file into `logs/signals/<name>/pending/`; a consumer moves it to `processed/`. Because nothing prunes `processed/`, this directory accumulates without bound — the 211K files here.
- `logs/event_spine.jsonl` — the append-only event spine stream.
- `logs/errors.jsonl`, `logs/model_router_errors.jsonl` — the error surfaces to grep first when a service misbehaves (Fix Forever discipline: every error here should be diagnosed and permanently fixed).
- `logs/cpu_watchdog.log` — output of the CPU-gate watchdog layer (see the CPU Gate Law); confirms the throttle guard is active.

## Data & state
All writes are append-only text/JSONL or per-signal JSON files. Rotation is available via `substrate/observability/jsonl_rotation.py` (`rotate_if_needed(path, max_lines=5000)`) — it moves an over-length JSONL into a timestamped archive and truncates the active file — but it is opt-in per writer, not a blanket sweep over `logs/`. The daily `morning_*/nightly_*` logs are never rotated; they accumulate one file per day. Nothing here is committed; the whole tree is gitignored.

## Gotchas
- **BROKEN symlink: `logs/logs → /opt/OS/_holding/logs`.** The target `/opt/OS/_holding/` does not exist, so this symlink is dangling. It is harmless (nothing resolves through it) but it is a doc/reality gap and shows up as a broken link in any traversal — flagged for [health findings](../health-findings.md). Either recreate `_holding/logs` or remove the symlink.
- **Runaway growth: 212,532 files, ~99% in `logs/signals/`.** The signal bus never prunes `processed/`. At 211K files this is already a directory-listing and inode-pressure risk on the VPS coordination node, and it violates Node Role Discipline (the VPS should stay lightweight). This is the single biggest cleanup target in `logs/` — a periodic sweep of `logs/signals/*/processed/` older than N days is the fix.
- **`data/logs` and `logs/` are the same files** (symlink). Don't double-count them across the two directory pages; the manifest counts the real `logs/` tree, and `data/logs` is a single link entry.
- **Logs are last in the retrieval hierarchy.** Per `CLAUDE.md`, never open `logs/` before you have exhausted Palace → Graph → Summaries → Raw Source. Grepping here is the debugging tool of last resort, not first.

## See also
- [`data/`](data.md) — hosts the `data/logs` symlink into this tree
- [`substrate/`](substrate.md) — signals/idempotency/decisions writers; `substrate/observability/jsonl_rotation.py`
- [`scripts/`](scripts.md) — `emit_signal.py`, `decisions.py`, cron loops that write daily logs
- [`services/`](services.md) — the daemons whose stderr/stdout land here
- [Health findings](../health-findings.md) · [Data flow](../data-flow.md)
