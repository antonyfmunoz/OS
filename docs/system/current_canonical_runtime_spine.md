# Current Canonical Runtime Spine

> Phase 96.8BJ — 2026-05-09 (updated 2026-05-11 post-R8h migration)
> Documents the actual runtime path and the target runtime path

---

## A. Current Actual Runtime

```
User message (Discord)
    │
    ▼
services/discord_bot.py                    ← PRIMARY ENTRYPOINT
    ├── on_message() / on_ready()
    ├── runtime.context.load_context_from_env()
    ├── runtime.gateway.EOSGateway
    │       ├── runtime.model_router.call_with_fallback()
    │       │       ├── CC SDK (priority 0, when available)
    │       │       ├── Gemini 2.5 Flash (primary fallback)
    │       │       └── Ollama qwen2.5:0.5b (local fallback)
    │       ├── runtime.memory.AgentMemory (Neon writes)
    │       └── runtime.memory.ConversationMemory (Neon writes)
    │
    ├── runtime.substrate.event_spine       ← Event routing
    ├── runtime.substrate.session_discord_bridge
    ├── runtime.substrate.discord_text_transport
    ├── runtime.substrate.storage.get_storage()
    │
    ├── runtime.runtime.work_state          ← Pressure tracking
    │       └── _measure_pressure() → Pressure enum
    │
    ├── handlers/substrate_command_handler  ← !commands
    │       ├── core.registry.*
    │       ├── core.control_plane_router.*
    │       └── core.workstation.*
    │
    └── data/runtime/                      ← Proof artifacts
            ├── proofs/
            ├── canonical_memory_store/
            └── [various proof directories]
```

### Import Chain (verified)
```
discord_bot.py
    → runtime.gateway
    → runtime.context
    → runtime.knowledge_integrator
    → runtime.voice_engine
    → runtime.business_instance
    → runtime.discord_utils
    → runtime.substrate.session_discord_bridge
    → runtime.substrate.discord_text_transport
    → runtime.substrate.event_spine
    → runtime.runtime.work_state
    → runtime.onboarding_engine
    → runtime.cc_sdk (lazy import)
```

### External Dependencies
```
Discord API ← discord.py library
Neon Postgres ← runtime.db (psycopg2)
Gemini API ← google.genai SDK
Ollama ← REST API (local)
Google Workspace ← runtime.gws_scanner (google-auth, googleapiclient)
```

---

## B. Target Runtime (Canonical Substrate Pipeline)

```
Signal (any source)
    │
    ▼
┌─ PERCEIVE ─────────────────────────────────┐
│  substrate/perception/                      │
│  Capture raw signal, normalize, timestamp   │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ INTERPRET ────────────────────────────────┐
│  substrate/interpretation/                  │
│  Intent classification, entity extraction   │
│  Context enrichment from world model        │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ DECOMPOSE ────────────────────────────────┐
│  substrate/decomposition/                   │
│  Primitive extraction (10 types)            │
│  Relationship mapping                       │
│  Confidence scoring                         │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ MAP TO ONTOLOGY ──────────────────────────┐
│  substrate/ontology/                        │
│  Canonical vs instance classification       │
│  Candidate generation                       │
│  Type-safe observation records              │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ PERSIST TO MEMORY / WORLD MODEL ──────────┐
│  substrate/memory/                          │
│  substrate/world_model/                     │
│  Promote candidates with governance receipt │
│  Update world model state                   │
│  JSONL → Neon migration path                │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ PLAN / COMPOSE ───────────────────────────┐
│  substrate/planning/                        │
│  substrate/composition/                     │
│  Goal decomposition, strategy selection     │
│  Action plan assembly                       │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ GOVERN ───────────────────────────────────┐
│  substrate/governance/                      │
│  Constitutional checks, budget enforcement  │
│  Authority level verification               │
│  Risk classification (LOW/MED/HIGH/CRIT)    │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ ROUTE CAPABILITY ─────────────────────────┐
│  substrate/capabilities/                    │
│  Match intent to abstract capability        │
│  Resolve to concrete adapter                │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ SELECT ADAPTER / ENVIRONMENT ─────────────┐
│  substrate/adapters/                        │
│  substrate/environments/                    │
│  Maturity-aware adapter selection           │
│  Environment availability check             │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ EXECUTE ──────────────────────────────────┐
│  substrate/execution/                       │
│  Governed action execution                  │
│  Timeout, retry, error handling             │
│  Result capture                             │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ TRACE / PROOF ────────────────────────────┐
│  substrate/observability/                   │
│  data/proofs/                               │
│  Execution trace with full provenance       │
│  Proof artifact with governance receipts    │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌─ OUTCOME → FEEDBACK / LEARNING ────────────┐
│  substrate/learning/                        │
│  Evaluate outcome against goal              │
│  Update confidence scores                   │
│  Feed back into world model                 │
└────────────────────────────────────────────┘
```

---

## C. Gap Analysis

| Gap | Current State | Target State | Severity |
|-----|--------------|--------------|----------|
| Scanner bypasses substrate | `gws_scanner.py` writes directly to `data/` | Scanner → perception → decomposition → memory | MEDIUM |
| Ingestion bridge partial | `gws_scanner_bridge_v1.py` bridges after extraction | Full perception → decomposition flow | LOW (bridge works) |
| Constitutional modules report-only | `constitutional_*_v1.py` generate reports | Governance layer gates runtime execution | MEDIUM |
| No perception layer | Signals enter via Discord event handler directly | Unified perception intake for all signal types | LOW |
| No composition layer | Gateway sends directly to LLM | Structured action plan before execution | MEDIUM |
| No capability routing | Commands mapped manually in handler | Capability registry → adapter selection | MEDIUM |
| `/umh` dormant | 870 Python files, zero runtime imports | Patterns migrated to substrate or archived | LOW |
| EOS platform island | `runtime/platform/` not connected to domain architecture | Platform layer consumes substrate contracts | LOW |
| Memory fragmented | `runtime.memory` (Neon) + `canonical_memory_store` (JSONL) | Unified memory layer in substrate | MEDIUM |
| Workstation unverified | Relay heartbeat/transport exist, actuation unproven | Verified workstation execution path | LOW |
| Test suite unclassified | 300+ test files, active mixed with legacy | Classified by layer and activity status | LOW |

---

## D. What Works Right Now

| Component | Status | Evidence |
|-----------|--------|----------|
| Discord bot | RUNNING | `docker ps` shows os-discord container |
| LLM routing | RUNNING | Gemini 2.5 Flash primary, Ollama fallback |
| Neon memory | RUNNING | AgentMemory + ConversationMemory write to Neon |
| GWS scanner | WORKING | 22/24 docs ingested, auth valid |
| Event spine | WORKING | Discord events route through substrate event spine |
| Ingestion bridge | WORKING | 1 real doc processed end-to-end (Phase 96.8BJ) |
| Canonical memory store | WORKING | 10 memories promoted with governance receipts |
| Work state/pressure | WORKING | Pressure tracking used by Discord bot |

---

## E. What Does NOT Work Yet

| Component | Status | Blocker |
|-----------|--------|---------|
| Constitutional enforcement | REPORT_ONLY | Generates reports, does not gate execution |
| Telegram bot | DORMANT | Service disabled, not in Docker |
| EOS platform runtime | DORMANT | Prototype exists, not connected |
| Adapter maturity scoring | FOUNDATION | Contracts exist, no runtime scoring |
| Workstation relay actuation | UNVERIFIED | Code exists, physical actuation unproven |
| Bulk ingestion | NOT_STARTED | Pipeline works for 1 doc, no batching |
| Neon memory migration | NOT_STARTED | JSONL store works, Neon migration planned |
| Semantic/embedding search | NOT_STARTED | Only exact-match queries available |
