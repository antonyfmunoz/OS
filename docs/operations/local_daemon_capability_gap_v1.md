# Local Daemon Capability Gap v1

**Date**: 2026-05-04
**Phase**: 93R.0 — Existing Local Daemon Discovery + Reconnection v1
**Purpose**: Compare existing daemon capabilities against what is needed for ingestion work orders.

---

## Capability Legend

| Tag | Meaning |
|-----|---------|
| PRESENT | Capability exists and is code-complete |
| PARTIAL | Some infrastructure exists but not complete for this use case |
| MISSING | No evidence of this capability in existing code |
| UNKNOWN | Cannot determine from VPS-side analysis |
| NEEDS_LOCAL_VERIFICATION | Capability exists in code but must be verified on local machine |

---

## Gap Analysis

### Needed Capability 1 — Local Worker Identity

| Field | Value |
|-------|-------|
| **Status** | PRESENT |
| **Evidence** | `station_daemon.py` uses `node_id="antony-workstation"`. `NodeRegistry` tracks node with capabilities, status, and metadata. `local_bridge_server.py` returns `{"machine": "local"}` in health check. |
| **Gap** | None for the station daemon system. The local bridge system has no formal worker identity — it's just an HTTP server. |
| **Usability for ingestion** | Station daemon identity is ready. Local bridge identity could be inferred from the Tailscale IP. |

### Needed Capability 2 — Work Order Intake

| Field | Value |
|-------|-------|
| **Status** | PARTIAL |
| **Evidence** | **Station daemon**: consumes `SafeAction` from StationBus outbox → structured work order intake exists, but only for 6 MVP action kinds (PLAY_SOUND, SPEAK_TEXT, OPEN_URL, LAUNCH_APP, OPEN_SCENE, FOCUS_APP). No `READ_FILE`, `EXPORT_DOC`, `NAVIGATE_BROWSER` kinds. **Local bridge**: accepts `POST /message` with `{text, session_name}` → unstructured text injection only. |
| **Gap** | Neither system accepts structured ingestion work orders. Station daemon has the framework (SafeAction + handler table) but not the action kinds. Local bridge has the transport but not the structure. |
| **Usability for ingestion** | Station daemon's handler table is extensible. Adding new `ActionKind` values + handlers is the designed extension path. |

### Needed Capability 3 — Queue Polling

| Field | Value |
|-------|-------|
| **Status** | PRESENT |
| **Evidence** | **Station daemon**: polls `StationBus` outbox every 1.0s (configurable). Atomic swap on read (daemon_take_outbox). **Task queue**: `task_queue.py` has priority-based queue with `operator_blocked` / `autonomous_day` / `approval_waiting` classifications. |
| **Gap** | Station daemon polling is functional but requires the bus files to be accessible on the local machine (currently VPS-local only, sync mechanism unknown). |
| **Usability for ingestion** | Polling infrastructure is ready. File sync to local machine is the gap. |

### Needed Capability 4 — Approval Gate

| Field | Value |
|-------|-------|
| **Status** | PARTIAL |
| **Evidence** | **ControlMode**: OBSERVE / ASSIST / DRIVE — ASSIST mode requires local confirmation per action. **approval_waiting queue**: task_queue.py defines the queue name. **authority_engine.py**: 4 risk classes with escalation. **cc_webhook_receiver `/cc-prompt`**: sends interactive prompts to Discord with buttons for approval. **MVP_ALLOWED_ACTIONS**: frozenset that must be explicitly widened. |
| **Gap** | No purpose-built "approve this ingestion work order" gate. The pieces exist (control mode, prompt forwarding, approval queue) but are not wired into an ingestion-specific workflow. |
| **Usability for ingestion** | The cc-prompt path (local → VPS → Discord buttons → response) is a working approval UI. The ControlMode.ASSIST pattern is the right model. Wiring needed, not building. |

### Needed Capability 5 — Read-Only Google Workspace Navigation/Export

| Field | Value |
|-------|-------|
| **Status** | PARTIAL |
| **Evidence** | **GWS Scanner** (`eos_ai/gws_scanner.py`): reads Google Docs via AI-based understanding, extracts business context, ingests to EOS. Scans up to 200 docs. **GWS Connector** (`eos_ai/gws_connector.py`): provides calendar, tasks, drive, gmail access via `gws` CLI. Circuit breaker with 5-min cooldown. |
| **Gap** | Both GWS tools run on VPS, not on the local machine. Google auth (`gws` CLI) is configured on VPS. For local-machine-only files (e.g., screenshots, local AI chat exports, non-cloud files), neither tool applies. |
| **Usability for ingestion** | VPS-side GWS tools can handle all Google Workspace ingestion without needing the local machine. Local machine is only needed for files that don't exist in Google Workspace. |

### Needed Capability 6 — AI Chat Export Support

| Field | Value |
|-------|-------|
| **Status** | MISSING |
| **Evidence** | No code found for parsing ChatGPT/Claude/Gemini export formats (JSON, markdown, HTML). No importer, no schema definition, no file-format detection. |
| **Gap** | Complete. Would need: format detection, parsing per platform, structured extraction, conflict resolution with existing EOS knowledge. |
| **Usability for ingestion** | Must be built. However, the local bridge can carry the raw export files to VPS for parsing — the parsing doesn't need to happen locally. |

### Needed Capability 7 — Local File Inventory

| Field | Value |
|-------|-------|
| **Status** | MISSING |
| **Evidence** | No code for scanning local filesystem structure, listing files by type/date/location, or building an inventory of what exists on the local machine. The station daemon has `local_filesystem` in its advertised capabilities but no actual file-read handler. |
| **Gap** | Complete. Would need: directory walker, file type classifier, metadata extractor, inventory output format. |
| **Usability for ingestion** | Could be added as a new `ActionKind.INVENTORY_LOCAL_FILES` handler in station_daemon.py, or as a simple script that runs locally and POSTs results to VPS. |

### Needed Capability 8 — Result/Evidence Writeback

| Field | Value |
|-------|-------|
| **Status** | PARTIAL |
| **Evidence** | **Station daemon → bus inbox**: `daemon_post_result()` writes `ActionResult` with structured `data` dict back to `node.inbox.json`. **Local bridge → VPS**: Stop hook POSTs CC reply text to `/cc-reply`. **Control bridge**: `acked` dict stores completed command results. |
| **Gap** | Result writeback exists for daemon action results (structured) and CC text replies (unstructured). Missing: file upload/transfer (sending a file from local to VPS), evidence attachment (screenshots, exports), structured ingestion result format. |
| **Usability for ingestion** | For text-based results (extracted content, inventory data), the existing `ActionResult.data` dict or the HTTP POST path works. For binary files, `tailscale file cp` or a new file upload endpoint would be needed. |

### Needed Capability 9 — Safety Confirmation

| Field | Value |
|-------|-------|
| **Status** | PRESENT |
| **Evidence** | **MVP_ALLOWED_ACTIONS**: explicit frozenset — action kinds not in the list are rejected. **ControlMode.ASSIST**: per-action local confirmation. **StationContract.propose()**: rejects non-allowed kinds. **dry_run mode**: `STATION_DAEMON_DRY_RUN=1` validates without executing. **Station daemon handler table**: only handlers in `_handlers` dict execute — adding kinds is a reviewable change. |
| **Gap** | None for the station daemon. The safety framework is well-designed: explicit allow-list, per-action approval, dry-run, bounded action vocabulary. |
| **Usability for ingestion** | The safety model is directly reusable. New ingestion action kinds would need to be added to the allow-list (a deliberate, reviewable code change) and given handlers that enforce read-only semantics. |

### Needed Capability 10 — No Secret Capture

| Field | Value |
|-------|-------|
| **Status** | PRESENT |
| **Evidence** | `LOCAL_BRIDGE_SETUP.md` §Security: "No secrets transmitted — only message text and session names." Station daemon handlers never access credential stores. SafeAction payloads are structured data, not arbitrary shell commands. |
| **Gap** | None. The architecture explicitly avoids secret transmission. The gap would be in any new handlers — they must maintain this property. |
| **Usability for ingestion** | Ready. New handlers must follow the same principle: no credential capture, no token transmission, no secret logging. |

### Needed Capability 11 — No Outbound Actions Without Approval

| Field | Value |
|-------|-------|
| **Status** | PRESENT |
| **Evidence** | **ControlMode.ASSIST**: every action requires local confirmation. **cc_webhook_receiver `/cc-prompt`**: interactive Discord buttons for approval. **Phase 91/92 governance**: 6 actions requiring founder approval. Station daemon's handler table is the boundary — it cannot execute anything not in the handler dict. |
| **Gap** | None at the architecture level. The approval gate exists. The governance model is defined. |
| **Usability for ingestion** | Ready. Ingestion work orders would flow through the same approval model: VPS proposes → founder approves → local executes read-only action → result returns. |

---

## Capability Summary

| # | Capability | Status | Notes |
|---|-----------|--------|-------|
| 1 | Local worker identity | PRESENT | Station daemon node_id + NodeRegistry |
| 2 | Work order intake | PARTIAL | SafeAction framework exists, ingestion action kinds missing |
| 3 | Queue polling | PRESENT | StationBus 1s polling, priority queue |
| 4 | Approval gate | PARTIAL | Pieces exist (ControlMode.ASSIST, cc-prompt, authority_engine), not wired for ingestion |
| 5 | Read-only GWS navigation/export | PARTIAL | VPS-side GWS tools exist, local-only files not covered |
| 6 | AI chat export support | MISSING | No parser for ChatGPT/Claude/Gemini exports |
| 7 | Local file inventory | MISSING | No local filesystem scanner |
| 8 | Result/evidence writeback | PARTIAL | Text results work, file transfer missing |
| 9 | Safety confirmation | PRESENT | MVP allow-list, dry-run, bounded vocabulary |
| 10 | No secret capture | PRESENT | Explicit design principle, enforced by architecture |
| 11 | No outbound without approval | PRESENT | ControlMode.ASSIST + cc-prompt + governance model |

**Present**: 5/11
**Partial**: 4/11
**Missing**: 2/11

---

## Gap Closure Estimate

| Gap | Effort | Approach |
|-----|--------|----------|
| Work order intake (complete) | LOW | Add 2-3 new ActionKind values + handlers to station_daemon.py |
| Approval gate (wire for ingestion) | LOW | Wire existing cc-prompt + approval_waiting queue into ingestion flow |
| GWS (local-only files) | MEDIUM | Add file-read handler to station daemon, or use tailscale file cp |
| AI chat export parser | MEDIUM | Build parser module for ChatGPT JSON, Claude JSONL, Gemini formats |
| Local file inventory | LOW | Add INVENTORY_LOCAL_FILES action kind or standalone script |
| Result/evidence writeback (files) | MEDIUM | Add file upload endpoint or use tailscale file cp with inbox pattern |

**Total estimated gap closure**: 1–2 build sessions if extending station daemon, or 1 session if using local bridge + simple scripts.
