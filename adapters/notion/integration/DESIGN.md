# Notion Integration — Design Report

Phase 0 = design. Phase 1 = create_page (implemented). Phase 2 = update_page, append_block, query_database (implemented).

---

## 1. Approach Decision: Direct SDK vs MCP Server

### Options

| Dimension | Direct SDK (`notion-client` 3.0.0) | MCP Server (`notion-mcp-server`) |
|---|---|---|
| **Auth complexity** | One env var (`NOTION_API_KEY`), already in `services/.env`. SDK handles header injection. | MCP server needs its own config + auth forwarding. Additional process to manage. |
| **Dependency surface** | Single dep (`notion-client`), already installed. Pulls `httpx`. | MCP server binary/package + MCP protocol lib + transport layer. At least 3 new deps. |
| **Debuggability** | Direct stack traces. `raw_error` in CapabilityResponse carries the exact `APIResponseError`. Rate limit headers visible in exception. | Two-hop debugging: UMH → MCP transport → MCP server → Notion API. Error provenance degraded. |
| **Hard Invariant 8 (Integration Boundary Exclusivity)** | Handler code lives in `services/umh/integrations/notion/handlers.py`. The import boundary is `notion_client` — a thin HTTP wrapper. No UMH internals leak outward. Clean structural Protocol satisfaction. | MCP server runs as a separate process. The boundary is the MCP transport, not the Python Protocol. UMH would need an MCP client adapter that satisfies `CapabilityHandler` — an extra translation layer that exists only to bridge two boundaries when one suffices. |
| **Portability (API changes)** | Notion SDK tracks API versions. Pin SDK version, update when Notion ships breaking changes. All translation logic in `transforms.py`. | Same API exposure, but now mediated through MCP server's own abstraction. If MCP server lags behind Notion API, we're blocked on upstream. |
| **Alignment with existing code** | `scripts/build_notion_workspace.py`, `scripts/build_notion_databases.py`, `eos_ai/notion_sync.py`, `eos_ai/notion_publisher.py` all use `notion_client.Client` directly. Pattern is established. | No MCP servers in the current stack. Would be the first, adding operational complexity with no existing playbook. |
| **Rate limiting** | Handled in handler code. 3 req/s Notion limit. `time.sleep(0.35)` between calls, or exponential backoff on 429. Transparent. | MCP server may or may not respect rate limits. No control without forking. |

### Recommendation: Direct SDK

The direct SDK wins on every axis that matters for this system. MCP adds a process boundary, a transport layer, and an abstraction that duplicates what the socket layer already provides. Hard Invariant 8 is satisfied cleanly by the handler implementing `CapabilityHandler` as a structural Protocol — the SDK is just an HTTP client behind the boundary. MCP would create a boundary-within-a-boundary with no gain.

The only scenario where MCP wins is if we needed to share the Notion connection with non-UMH consumers over a standard protocol. We don't. UMH is the sole consumer.

---

## 2. Manifest Structure

```
services/umh/integrations/notion/
├── __init__.py          # Existing. Module docstring, future re-exports.
├── manifest.py          # Existing. Signal + Capability descriptors. UMH-owned config.
├── handlers.py          # NEW. NotionCapabilityHandler implementing CapabilityHandler Protocol.
├── transforms.py        # NEW. Notion API ↔ UMH payload translations.
├── signals.py           # NEW. NotionSignalEmitter implementing SignalEmitter Protocol.
├── outcomes.py          # NEW. NotionOutcomeReceiver implementing OutcomeReceiver Protocol.
├── routing.py           # NEW. Signal routing rules (which Notion events map to which content_types).
├── auth.py              # NEW. Auth config loader. Reads NOTION_API_KEY from env.
└── DESIGN.md            # This file.
```

### Pattern alignment

This matches the per-integration config-directory pattern from the socket design:
- `manifest.py` declares descriptors (already exists with 3 signals + 3 capabilities)
- `handlers.py` contains the `CapabilityHandler` implementation that calls `notion_client`
- `transforms.py` handles payload shape conversion between Notion's JSON and UMH envelope schemas
- `signals.py` / `outcomes.py` implement the remaining Protocol faces
- `routing.py` maps Notion event types to UMH signal content_types
- `auth.py` isolates credential loading (single responsibility for the env-var → Client path)

No file in this directory imports UMH internals beyond the socket envelope types and Protocol shapes. The import graph points inward (UMH → integration), never outward.

---

## 3. Signal Flow

### Notion events → UMH signals

For Phase 1, signals are **poll-based** (no webhooks). A poller queries Notion's `search` or `database.query` endpoints on an interval and emits signals for detected changes.

| Notion Event | `content_type` | Default Urgency | Default Risk Class | Notes |
|---|---|---|---|---|
| Page created | `page_created` | NORMAL | READ_ONLY | Already in manifest.py |
| Page updated | `page_updated` | LOW | READ_ONLY | Already in manifest.py |
| Database entry added | `database_entry_added` | NORMAL | READ_ONLY | Already in manifest.py |
| Status property changed | `status_changed` | NORMAL | READ_ONLY | Phase 2. Filtered from page_updated. |
| Comment added | `comment_added` | HIGH | READ_ONLY | Phase 2. Requires comment API access. |
| Database entry updated | `database_entry_updated` | LOW | READ_ONLY | Phase 2. |

### SignalEnvelope schema for Notion signals

```python
SignalEnvelope(
    integration_id="notion",
    content_type="page_created",         # from routing table above
    payload={
        "page_id": "abc-123",            # Notion page UUID
        "title": "Q2 Pipeline Review",   # extracted from title property
        "database_id": "def-456",        # parent database, if any
        "properties": { ... },           # full Notion properties dict
        "url": "https://notion.so/...",  # canonical URL
        "created_by": "user-789",        # Notion user ID
    },
    raw_content=None,                    # or JSON string of full Notion response
    source_identifier="notion:page:abc-123",
    correlation_id=None,                 # set if this signal is a response to a prior action
    urgency=SignalUrgency.NORMAL,
    metadata={
        "notion_last_edited": "2026-05-19T10:30:00Z",
        "poll_cycle_id": "cycle-001",
    },
)
```

### Correlation ID propagation

When UMH creates a page via `create_page` capability and later detects that page in a poll cycle, the `correlation_id` on the inbound signal is set to the `request_id` from the original `CapabilityRequest`. This is tracked via a local correlation map in the handler:

```
CapabilityRequest.request_id  →  page_id created
                                      ↓
poll detects page_id  →  SignalEnvelope.correlation_id = original request_id
                                      ↓
OutcomeEnvelope.correlation_id carries through pipeline
```

This enables the outcome receiver to close the loop: "I created this page, and now I see it exists."

---

## 4. Capability Handler

### `NotionCapabilityHandler.handle_capability(request)`

The handler receives a `CapabilityRequest`, extracts `capability_name` and `params`, calls the appropriate Notion SDK method via `transforms.py`, and returns a `CapabilityResponse`.

```
CapabilityRequest arrives
    → validate params against input_schema (from manifest.py)
    → transform params via transforms.py (UMH shape → Notion API shape)
    → call notion_client method
    → transform response via transforms.py (Notion response → UMH shape)
    → return CapabilityResponse(success=True, result_data=transformed)
```

On exception:
```
    → return CapabilityResponse(
        success=False,
        error="create_page failed: invalid database_id",    # sanitized
        raw_error="APIResponseError: 400 validation_error",  # raw Notion error
        latency_ms=elapsed,
    )
```

### Implemented operations (Phase 1 + Phase 2)

| Capability | Category | Risk Class | Input | Output | Phase |
|---|---|---|---|---|---|
| `create_page` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{title, database_id, properties}` | `{page_id, url}` | 1 |
| `update_page` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{page_id, properties}` | `{page_id, updated: bool}` | 2 |
| `append_block` | COMMUNICATE | EXTERNAL_COMMUNICATION | `{page_id, children: list[block]}` | `{block_ids: list, count: int}` | 2 |
| `query_database` | RETRIEVE | READ_ONLY | `{database_id, filter?, sorts?, page_size?}` | `{results: list, count: int, has_more: bool}` | 2 |

### Future operations (parked)

| Capability | Category | Notes |
|---|---|---|
| `get_page` | RETRIEVE | READ_ONLY. Single page retrieval by ID. |
| `delete_page` (archive) | COMMUNICATE | IRREVERSIBLE_WRITE. Needs explicit governance rule. |
| `create_database` | COMMUNICATE | EXTERNAL_COMMUNICATION. Heavy operation. |
| `add_comment` | COMMUNICATE | EXTERNAL_COMMUNICATION. Requires comment API. |
| `search` | RETRIEVE | READ_ONLY. Full-text search across workspace. |
| `get_database_schema` | RETRIEVE | READ_ONLY. Introspection for dynamic form building. |
| `bulk_update` | COMMUNICATE | EXTERNAL_COMMUNICATION. Batch property updates with rate limiting. |

### Health check

`NotionCapabilityHandler.health()` calls `client.users.me()` — a zero-side-effect authenticated endpoint. Returns `CapabilityHealth(status="healthy")` on 200, `"degraded"` on timeout, `"unavailable"` on auth failure.

---

## 5. Outcome Flow

### `NotionOutcomeReceiver.on_outcome(envelope)`

The outcome receiver maps pipeline outcomes back to Notion-side effects. This is fire-and-forget per the `OutcomeSocket` contract.

### Outcome → Notion mapping

| `outcome_type` | Notion Side Effect | Notes |
|---|---|---|
| `execution_success` | Update source page status property to "Processed" | Only if `result_data` contains `page_id` |
| `execution_failure` | Update source page status to "Error" + append error block | Sanitized `error`, not `raw_error` |
| `governance_denied` | Update source page status to "Blocked" | Append `governance_decision` as comment block |
| `execution_timeout` | Update source page status to "Timeout" | Append retry guidance |

### Error distinction

- `error` (sanitized): written to Notion page as a status update. Safe for human consumption. Example: `"create_page failed: invalid database_id"`
- `raw_error` (raw): kept in UMH trace store only. Contains Notion API error codes, rate limit headers, stack traces. Used for retry logic in the handler. Example: `"APIResponseError: 429 rate_limited, retry-after: 2"`

The outcome receiver uses `raw_error` to decide whether to retry (429 → yes, 400 → no) but never writes it to Notion.

### `accepts_outcomes()`

Returns `["execution_success", "execution_failure", "governance_denied", "execution_timeout"]`. Ignores memory and trace outcomes that don't need Notion-side effects.

---

## 6. View Implications

### Signal flow through master loop

Notion signals enter at Stage 1 (signal) via the SignalSocket and flow through all 10 stages identically to any other signal. The `integration_id="notion"` field on the `ViewFrame` identifies them.

```
Stage 1: signal        → ViewFrame(event_type="signal", integration_id="notion", data={signal payload})
Stage 2: governance    → ViewFrame(event_type="governance", data={verdict, risk_class})
Stage 3: work_packet   → ViewFrame(event_type="work_packet", data={packet_id, adapter="notion"})
Stage 4: execution     → ViewFrame(event_type="execution", data={capability_name, latency_ms})
Stage 5: proof         → ViewFrame(event_type="proof", data={proof_id, proof_type})
Stage 6: outcome       → ViewFrame(event_type="outcome", data={outcome_type, summary})
Stage 7: trace         → ViewFrame(event_type="trace", data={trace_id})
Stage 8-10: memory     → standard memory candidate/promote/resume
```

### Cockpit TraceStream

No new `ViewFrame` shapes needed. The existing `ViewFrame` dataclass has all required fields:
- `integration_id: str | None` — set to `"notion"` for Notion-originated frames
- `event_type: str` — uses existing stage names from `STAGE_NAMES`
- `data: dict[str, Any]` — carries Notion-specific payload

The cockpit can filter by `integration_id == "notion"` to show a Notion-specific trace stream. This is a cockpit UI concern, not a socket layer concern.

### One potential addition (deferred)

If we want the cockpit to show Notion API rate limit state (current request count, remaining budget, retry-after), the handler could emit a custom `ViewFrame` with `event_type="notion_rate_limit"` and `stage=0` (out-of-band). This would require the handler to hold a reference to the `ViewSocket` — which breaks the current pattern where only the pipeline emits frames. **Deferred to Phase 3.** The handler can log rate limit state instead.

---

## 7. Auth Model

### Current state

`NOTION_API_KEY` is already set in:
- `services/.env` (line 54)
- `runtime/.env` (line 54)

`NOTION_TOKEN` is set in:
- `runtime/.env` (line 114)

There are 60+ `NOTION_*_ID` env vars for database and page IDs across both env files.

### Design decision

The Notion handler loads auth from `services/.env` via `python-dotenv`, matching the pattern used by existing services (`discord_bot.py`, `dm_monitor.py`, etc.). No separate `services/umh/integrations/notion/.env` file.

```python
# auth.py
def get_notion_client() -> Client:
    load_dotenv("/opt/OS/services/.env")
    key = os.getenv("NOTION_API_KEY")
    if not key:
        raise RuntimeError("NOTION_API_KEY not set in services/.env")
    return Client(auth=key)
```

### Database ID resolution

Database IDs are loaded from env vars at handler initialization, not hardcoded. The handler exposes a `databases` property that maps logical names to UUIDs:

```python
{
    "lyfe_tasks": os.getenv("NOTION_LYFE_INSTITUTE_TASKS_DB"),
    "empyrean_tasks": os.getenv("NOTION_EMPYREAN_CREATIVE_TASKS_DB"),
    "brand_tasks": os.getenv("NOTION_PERSONAL_BRAND_TASKS_DB"),
    ...
}
```

Callers pass logical database names in `CapabilityRequest.params["database_id"]`. The handler resolves to the actual UUID. This decouples UMH from Notion workspace structure.

### Deferred-auth alignment

Per the socket design's deferred-auth decision: we are not at remote integrations yet. Auth is local (env var on the VPS). No OAuth flows, no token refresh, no multi-tenant auth. When remote integrations arrive, the `auth.py` module is the single point that changes — the handler doesn't know where the token came from.

---

## 8. Phase Split

### Phase 1: Manifest + Handler + End-to-End Single Operation ✓ IMPLEMENTED

**Goal:** One capability (`create_page`) flows through the full pipeline — signal in, governance check, adapter execution, proof, outcome, trace.

- Wire `handlers.py` with `NotionCapabilityHandler` implementing `CapabilityHandler` Protocol
- Wire `auth.py` for credential loading
- Wire `transforms.py` for `create_page` input/output transforms
- Wire `signals.py` with `NotionSignalEmitter` (declares signal types, no polling yet)
- Wire `outcomes.py` with `NotionOutcomeReceiver` (logs outcomes, no Notion writeback yet)
- Register manifest in `IntegrationRegistry` via startup wiring
- Add `create_page` + `get_page` + `query_database` capabilities
- Tests: handler unit tests, transform tests, integration test via curl → pipeline
- Verify: `curl` to DEX → Notion page created → trace visible in cockpit

### Phase 2: Expanded Operations ✓ IMPLEMENTED

**Goal:** Add `update_page`, `append_block`, `query_database` operations to NotionCapabilityHandler.

Implemented:
- `update_page` — update properties on an existing page (EXTERNAL_COMMUNICATION risk)
- `append_block` — append content blocks to a page (EXTERNAL_COMMUNICATION risk)
- `query_database` — query with filters/sorts, return matched pages (READ_ONLY risk)
- Transform functions: build payload + extract result for each operation
- 27 new tests (11 transform tests + 16 handler tests) — 173 total passing
- Smoke script extended: `SMOKE_OPS="create,update,append,query"` for multi-op testing
- Each operation follows create_page pattern: validate → transform → SDK call → extract
- 429 retry with 2s backoff inherited from shared `_retry_once()` path
- Outcome writeback and signal routing deferred to Phase 4 and Phase 3 respectively

### Phase 3: Signal-Direction Adapters (Inbound Polling) ✓ IMPLEMENTED

**Goal:** UMH detects Notion changes and ingests them as signals.

Implemented:
- `WatermarkStore` — thread-safe JSONL append-log at `services/umh/data/notion_watermarks.jsonl`. Per-database high-water mark on `last_edited_time`. Latest entry per database wins on load.
- `NotionPoller` — background daemon thread polling configured databases. Query pages with `last_edited_time > watermark` (ascending), paginated. One retry on 429. Controlled by `threading.Event` for shutdown.
- `NotionSignalEmitter` — real implementation replacing stub. `build_signal(page, config)` → `(SignalEnvelope, writeback_to)` with correlation_id for outcome routing.
- `_noop` handler — acknowledges polled signals without external action. Pipeline runs full 10 stages, returns success.
- `NOTION_SIGNAL_SOURCES` env var — comma-separated database logical names. Each defaults to `operation="noop"`, `poll_interval=30s`.
- Poller started in FastAPI lifespan (daemon thread), stopped on shutdown via `threading.Event.set()` + `thread.join(timeout=5)`.
- Correlation map populated per-signal, outcome writeback fires on pipeline completion (Phase 4 path reused).
- Smoke script: `SMOKE_OPS="signal"` creates page in polled DB → waits poll interval → verifies UMH Status set by writeback.
- 12 new poller tests, 10 watermark tests, 16 signal emitter tests, 3 noop handler tests.

**Env var format:** `NOTION_SIGNAL_SOURCES=empyrean_creative_tasks,lyfe_tasks`
**Watermark location:** `services/umh/data/notion_watermarks.jsonl`

### Phase 4: Outcome Writeback ✓ IMPLEMENTED

**Goal:** Pipeline outcomes write status back to Notion pages — dual effect: "UMH Status" select property + callout block with outcome details.

Implemented:
- `CorrelationMap` — thread-safe in-memory `dict[UUID, WritebackTarget]` for mapping correlation IDs to Notion pages
- `WritebackTarget` — frozen dataclass: `page_id: str`, `integration: str = "notion"`
- `NotionOutcomeReceiver` — real implementation replacing Phase 1 stub. Uses Notion SDK directly (writebacks are outcome side-effects, not new signals — no governance reentry)
- Status mapping: success→"Success", failure/error→"Error", governance_denied→"Blocked", timeout→"Timeout", unknown→"Unknown"
- Callout block: `[UMH] {outcome_type}: {summary}\ntrace: {trace_id}` with emoji (🔔 success, ⚠️ other)
- One retry on 429 with 2s backoff inside the receiver
- `/api/umh/submit` extended with optional `writeback_to: {page_id, integration}` field
- Correlation map populated at submit time, consumed at outcome time
- 21 new tests (6 correlation map + 15 outcome receiver) — 194 total passing
- Smoke script: `SMOKE_OPS="writeback"` creates page → submits with writeback_to → verifies status property + callout block

**Convention:** Notion databases that receive writeback must have a "UMH Status" select property with options: Success, Error, Blocked, Timeout, Unknown. The property is created automatically by Notion when the first writeback sets it.

### Phase 5: Advanced Operations + Bulk (future)

**Goal:** Delete, search, bulk update, database creation.

- `delete_page`, `search`, `create_database`, `bulk_update` capabilities
- Governance rules for `IRREVERSIBLE_WRITE` operations
- Batch rate limiting for bulk operations

---

## 9. Open Decisions

### Resolved (Phase 1)

1. **Registration wiring:** DECIDED — `IntegrationRegistry.register()` at app startup. The resulting `IntegrationAdapter` is passed to `WorkPacketExecutor.register_adapter()`. This is the designed path; local adapters predate the socket layer and register directly only because they lack signals/outcomes.

2. **Logical database name mapping:** DECIDED — derive from env var naming convention. Strip `NOTION_` prefix and `_DB`/`_ID` suffix, lowercase, join with underscore. Adding a new database = adding an env var, no code change.

3. **Error retry policy:** DECIDED — one retry with backoff inside the handler on 429. Retry logic is Notion-specific knowledge that doesn't belong in the socket layer. Handler retries once, then lets it fail. Socket layer still catches unexpected exceptions via its existing normalization.

4. **Test strategy:** DECIDED — mock `notion_client.Client` for unit tests (CI suite). One manual smoke test script hits the real API against existing databases using `[UMH-TEST]` title prefix. No dedicated test database.

### Resolved (Phase 4)

5. **Outcome writeback target:** DECIDED — hardcoded "UMH Status" select property on originating Notion page. Notion auto-creates the select option on first write. Convention-based: databases that receive writeback must have this property.

### Resolved (Phase 3)

6. **Signal deduplication:** DECIDED — per-database watermark on `last_edited_time`, persisted to JSONL append-log. Poller queries pages with `last_edited_time > watermark` and advances watermark after processing.

7. **Poll interval:** DECIDED — 30s default, configurable per signal source. With `NOTION_SIGNAL_SOURCES` controlling which databases are polled, API budget is bounded.

8. **Poller thread model:** DECIDED — dedicated daemon thread in UMH process, started in FastAPI lifespan, controlled by `threading.Event` for shutdown. Preserves correlation context.

9. **Correlation map persistence:** DECIDED — in-memory only for Phase 3. Process restart clears map. Acceptable for current scale.
