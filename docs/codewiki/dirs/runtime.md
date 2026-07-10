---
type: codewiki-dir
dir: runtime
---

# `runtime/` — gitignored live substrate state (station bus + voice sessions)

**2 files · ~48 MB · [Full file inventory](../inventory/runtime.md)**

*(Counts as of the manifest's `generated_at` 2026-07-10T20:18Z, git SHA `a5f09e48e`. Two files, but large: the station inbox alone is tens of MB and is rewritten continuously.)*

## Purpose
`runtime/` holds the substrate's *live*, transient execution state — the file-backed default for two mechanisms that need durable-across-restart storage without a database. It is fully gitignored (`.gitignore` line 160, `runtime/`) because its contents are pure runtime churn: they are recreated on demand by the writers and are meaningless outside a running system. This is deliberately separate from `data/` (curated/operational state) and `logs/` (append-only exhaust): `runtime/` is the small set of *current* state blobs the execution layer rewrites in place.

## How it fits
Written by `substrate/execution/bridge/*` and read back by the same layer plus the presence transport. It imports nothing; the execution bridge opens these paths, resolved from `UMH_ROOT` (default `/opt/OS`). Because it is the file-backed *default* store, it is the fallback when no external state backend is configured — the "safe default" noted in `substrate/execution/bridge/storage.py`.

## Structure

| Path | Written by | Role |
|---|---|---|
| `.substrate_state.json` | `substrate/execution/bridge/storage.py` (`_JSON_PATH = {root}/runtime/.substrate_state.json`) | The substrate state blob. Current top-level content is `voice_sessions` — live voice session state persisted across restarts. |
| `.substrate_station/` | `substrate/execution/bridge/station_bus.py` (`_BUS_DIR = {root}/runtime/.substrate_station`) | The station message bus: per-node `<node_id>.inbox.json` / `<node_id>.outbox.json`. Cross-node execution messages queued between the coordination brain and executor nodes. |

## Key components
- `substrate/execution/bridge/storage.py` — owns `.substrate_state.json`. Its module docstring names this file as the "safe default: JSON file at `/opt/OS/runtime/.substrate_state.json`", i.e. the fallback state backend.
- `substrate/execution/bridge/station_bus.py` — owns `.substrate_station/`. Defines the inbox/outbox file convention (`{node_id}.inbox.json`, `{node_id}.outbox.json`) that carries messages between mesh nodes.
- `transports/presence/handlers/substrate_command_handler.py` and `substrate/execution/workers/workstation/relay_execution_transport_v1.py` also read/write this state — they are the presence and workstation-relay consumers of the bus.

## Data & state
File-backed JSON only. Writes are atomic-via-temp: the station bus writes `<node_id>.inbox.json.tmp` and renames over the live file, so a `.tmp` sibling briefly appearing next to a large `.inbox.json` is normal mid-write behavior, not corruption. The inbox can reach tens of MB because it is a queue of serialized messages; it drains as consumers process. No Neon dependency — this is the local, in-process durable store.

## Gotchas
- **Entirely gitignored and correct to be so.** `runtime/` never belongs in git — it is live state. Do not add it. If you see it in a diff, something removed the ignore rule.
- **`.inbox.json` can be large and grow fast.** A tens-of-MB inbox means messages are queued and not yet drained; that is a consumer-lag signal, not a bug in the file itself. Watch it under sustained cross-node load — it is the station bus's backpressure indicator.
- **Not the same "runtime" as `data/runtime/`.** `data/runtime/` (also gitignored, `.gitignore` line 121) holds generated runtime proofs/examples; top-level `runtime/` here holds live substrate/bus state. Two different concerns, both transient. See [`data/`](data.md).
- **Node role discipline applies.** The station bus is how the VPS coordination brain talks to executor nodes; keep the VPS side lightweight and let heavy work drain to executors rather than backing up here.

## See also
- [`data/`](data.md) — has a separate gitignored `data/runtime/` for generated proofs
- [`substrate/`](substrate.md) — `execution/bridge/storage.py`, `execution/bridge/station_bus.py`
- [`transports/`](transports.md) — presence handler that consumes the bus
- [Services & runtime](../services-runtime.md) · [Data flow](../data-flow.md)
