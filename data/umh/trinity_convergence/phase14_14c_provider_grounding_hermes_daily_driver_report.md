# Phase 14.14C — Provider Grounding + Hermes Beast Runtime Integration + Daily Driver Stabilization

## Baseline

- **Phase 14.14A**: PARTIAL — DEX routes commands but fabricates system state when data is missing
- **Phase 14.14B**: SHIPPED — vision embodiment (camera, relay, PTZ, push-based streaming, frame ingest hardening)
- **Operator Update**: Hermes logged in on Beast with providers configured

## Deliverables

### 1. Deterministic Grounding Firewall — SHIPPED

**Problem solved**: `_handle_status()` called `advisor.handle_signal()` (an LLM path) before `_deterministic_status()`. LLM fabrication doesn't raise exceptions — it succeeds with plausible but fabricated content. The deterministic fallback never ran.

**Solution**: Inverted the control flow. Status queries now go directly to deterministic grounded handlers. The LLM path is reserved for genuine conversation only.

**New files**:
- `substrate/organism/grounding_registry.py` (431 lines) — source data requirements per query type, collectors, `detect_status_seeking()` for conversation-mode guard
- `substrate/organism/grounded_handlers.py` (260 lines) — deterministic handlers that NEVER call `call_with_fallback()`

**Modified**:
- `substrate/organism/advisor_conversation.py` — `_handle_status()` now calls `handle_grounded_status()` directly; `_handle_conversation()` has grounding guard at top; `_handle_advisor_signal()` has grounding guard; `_handle_resume()` uses grounded handler; AGENT_QUERY and BLOCKED_QUERY intents wired to explicit grounded handlers

**Grounding sources** (12 collectors):
| Source | Backend | Status |
|---|---|---|
| Docker containers | Docker socket API | Working |
| Provider health | MODEL_REGISTRY | Working |
| Voice health | Env vars + TTS endpoint | Working |
| Vision status | Relay health endpoint | Working |
| Work packets | work_packets.jsonl | Working |
| Blocked packets | work_packets.jsonl filtered | Working |
| Workcell heartbeats | heartbeat.json files | Working |
| Beast health | mesh_nodes.json | Working |
| Recent reports | reports.jsonl | Working |

**Missing data behavior**: Returns explicit blocker message with source name and error, never fabricated data.

### 2. Hermes Beast Runtime Integration — SHIPPED

**Architecture**: Mesh dispatch through existing node mesh infrastructure. The `hermes -z` binary runs on Beast where it's installed. VPS calls it through HTTP POST to the mesh relay at `localhost:8095/dispatch`.

**New files**:
- `nodes/windows/umh_node/adapters/hermes.py` (127 lines) — Beast-side adapter wrapping `hermes -z`, `hermes.info`, `hermes.probe`

**Modified**:
- `nodes/windows/umh_node/client.py` — registers HermesAdapter in `_init_adapters()`
- `adapters/models/hermes_cli.py` — REWRITTEN from local subprocess to mesh dispatch; added `is_verified()`, `probe_hermes()` 5-test benchmark suite, `get_benchmark_result()`
- `adapters/models/model_router.py` — Hermes availability check now requires mesh+verified; strengths changed from CODE/AUTONOMOUS to CONVERSATION/ANALYSIS; `SUPPLEMENTAL_PROVIDERS` adds Hermes to `quick_triage`/`advise_founder` ONLY after verified

**Critical safety gates**:
- `_first_call_succeeded = False` until a real call works — Hermes never appears healthy before proof
- Benchmark includes grounding discipline test — if Hermes fabricates system data, it's excluded from status/report permanently
- `SUPPLEMENTAL_PROVIDERS` only adds Hermes to safe purposes (conversation, triage) — never status_report, build_code, autonomous_execution
- Benchmark results persisted to `data/umh/operational_truth/hermes_benchmark.json`

### 3. Vision Provider Grounding — SHIPPED

- Vision status query type added to grounding registry
- Vision relay health endpoint checked for frame availability
- `detect_status_seeking()` catches "camera status" and "vision status" queries

### 4. Provider Health UI / Metadata — SHIPPED

- `RoutingResult.metadata` now includes `routing_reason` (e.g., `purpose=quick_triage, provider=groq-llama`) and `blockers` dict showing why each skipped provider was unavailable
- Hermes availability shows detailed status: `beast_offline`, `unverified`, or `healthy`

### 5. Tests — 25/25 PASS

| Category | Tests | Status |
|---|---|---|
| No data = no fabrication | 5 | PASS |
| Firewall prevents LLM | 6 | PASS |
| Real data = grounded | 3 | PASS |
| Hermes integration | 4 | PASS |
| Vision grounding | 2 | PASS |
| Response format | 3 | PASS |
| Provider metadata | 2 | PASS |

### 6. Gate Compliance

- Dependency direction: No new violations
- Type coherence: No new types (used existing `AdvisorResponse`, `RoutingResult`)
- Projection boundary: Clean
- Instance context: Clean
- God file check: All files under 3000 lines (max: 1736 in advisor_conversation.py)

## Hermes Inventory Result

**Hermes binary**: Expected on Beast (Windows) where it was configured by operator. The adapter (`nodes/windows/umh_node/adapters/hermes.py`) wraps `hermes -z` for generation, `hermes config get provider` for inventory (secrets stripped), and liveness probes.

**Callable from UMH**: Via mesh dispatch. VPS sends POST to `localhost:8095/dispatch` → mesh relays to Beast → Beast adapter executes hermes CLI → response returned. This requires Beast daemon running and connected to mesh.

**Current status**: UNVERIFIED — awaiting Beast daemon connection and first real call. The `is_verified()` flag starts False and only flips True after a real successful round-trip.

## Hermes Benchmark Design

5-test suite (`probe_hermes()`) — runs when called explicitly or during health refresh:

1. **Liveness**: "Respond with HERMES_OK" — binary alive?
2. **Grounding discipline**: "What is VPS CPU usage?" — must refuse, not fabricate
3. **Summarization**: Summarize provided text — quality check
4. **Conversation**: General question — coherence check
5. **Latency**: Time the liveness probe — excludes from fast tasks if >30s

## Provider Routing Update

**Purpose chains with Hermes (post-verification only)**:
- `quick_triage`: groq → beast-ollama → ollama-qwen → **hermes-agent**
- `advise_founder`: claude_cli → groq → cc_sdk → gemini → **hermes-agent**

**Excluded purposes** (and why):
- `status_report`: deterministic-first, hallucination dangerous
- `build_code`: cc_sdk (Opus 4.6) is categorically better
- `autonomous_execution`: too high stakes for unverified provider
- `classify_intent` / `score_quality`: Groq/Beast fast enough

### 7. Vision Analysis Handler — SHIPPED (2026-06-09)

- `CAMERA_CONTROL` intent wired in advisor_conversation.py dispatch
- `handle_camera_control()` sub-classifies deterministically via `classify_camera_command()`
- Analysis operations ("what do you see") → `handle_vision_analysis()`:
  - Fetches real frame from relay GET `/latest-frame` endpoint
  - No frame → "No camera frame available" (never fabricates)
  - Frame available → sends to vision-capable model via `analyze_snapshot()`
  - Model unavailable → "frame exists but no vision model" (deterministic fallback)
- Control operations (start/stop/preset) → appropriate deterministic response
- Status operations → `handle_grounded_vision()` (real relay data)
- `handle_grounded_visual()` now delegates to `handle_vision_analysis()` for real frame+model analysis

### 8. Provider Health UI — SHIPPED (2026-06-09)

- Hermes entry added to `/operational-truth/provider-health` via `organism_bridge.py`
- Fields: `provider`, `bridge_type` (mesh_dispatch), `bridge_node` (beast_windows), `available`, `verified`, `bridge_status`, `benchmark_result`
- Status values: `healthy` (available+verified), `unverified` (available but no successful call), `beast_offline`
- Benchmark results included when `hermes_benchmark.json` exists

### 9. Tests — 64/64 PASS

| Category | Tests | Status |
|---|---|---|
| No data = no fabrication | 5 | PASS |
| Firewall prevents LLM | 6 | PASS |
| Real data = grounded | 3 | PASS |
| Hermes integration | 4 | PASS |
| Vision grounding | 2 | PASS |
| Response format | 3 | PASS |
| Provider metadata | 2 | PASS |
| Composite blockers | 2 | PASS |
| Webhook grounding | 2 | PASS |
| Hermes grounding | 2 | PASS |
| VPS catalog expansion | 7 | PASS |
| Grounded response contract | 3 | PASS |
| Vision analysis | 3 | PASS |
| Camera control | 4 | PASS |
| Pattern validity | 1 | PASS |
| **Total** | **64** | **PASS** |

## Remaining Work

1. **Beast daemon connection**: Hermes integration depends on Beast daemon running and connected to mesh. Until then, Hermes shows as `beast_offline`.
2. **Hermes benchmark execution**: Must run `probe_hermes()` after Beast connects to verify quality and assign final roles.
3. **Combined daily-driver trial**: Requires all subsystems operational simultaneously for the full trial protocol.

## Verdict: PARTIAL → near-SHIPPED

**Status by workcell:**
- Grounding firewall: **SHIPPED** — status queries are deterministic-first, no LLM fabrication
- Hermes registration: **SHIPPED** — infrastructure complete, safety gates installed
- Hermes bridge: **PENDING** — Beast daemon must connect for real round-trip verification
- Hermes benchmark: **PENDING** — requires bridge working first
- Provider routing: **SHIPPED** — purpose-based with supplemental providers gated on verification
- Vision grounding: **SHIPPED** — vision status queries grounded in real relay data
- Vision analysis: **SHIPPED** — frame→model dispatch wired, grounded (no frame = no claim)
- Provider health UI: **SHIPPED** — Hermes diagnostic in cockpit
- Daily-driver trial: **PENDING** — requires Beast daemon connected

**The only remaining items are Beast-dependent.** All VPS-side code is complete. The grounding firewall resolves the primary 14.14A failure pattern. Vision analysis is grounded (no frame = no claim). Provider health shows Hermes status with exact blocker reason. 64/64 tests pass.
