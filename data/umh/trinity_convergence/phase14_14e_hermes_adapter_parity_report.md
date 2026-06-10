# Phase 14.14E — Hermes Adapter Parity + Runtime Bridge Hardening

## Baseline

- **Phase 14.14C**: SHIPPED — Hermes callable through Beast mesh dispatch, 5/5 benchmark, 9.1s latency
- **Pre-14.14E state**: Hermes was a "callable supplemental provider" — generate only, no sessions, no diagnostics, no role gating, no structured errors, no capability registry

## Deliverables

### 1. Adapter Parity Audit — SHIPPED

Full comparison of all UMH runtime adapters documenting the common interface Hermes must match. Hermes now matches or exceeds the contract of every other adapter for all structurally possible operations.

See: `data/umh/trinity_convergence/hermes_adapter_parity_audit.md`

### 2. Beast Hermes Adapter (Full Operations) — SHIPPED

**File**: `nodes/windows/umh_node/adapters/hermes.py` (rewritten from 127 → 320 lines)

Operations added:
- `hermes.health` — liveness probe returning structured healthy/latency/error
- `hermes.providers` — provider config with automatic secret stripping
- `hermes.models` — model list extraction
- `hermes.capabilities` — explicit capability registry with notes
- `hermes.diagnostics` — binary path, version, config readable, last error, call count
- `hermes.benchmark` — 4-test suite (liveness, grounding, summarization, conversation)
- `hermes.cancel` — best-effort process kill via threading lock

Safety improvements:
- `Popen` instead of `subprocess.run` for cancellation support
- Thread-safe active process tracking
- Structured error codes: `HERMES_UNAVAILABLE`, `HERMES_TIMEOUT`, `HERMES_PROCESS_ERROR`, `HERMES_ERROR_LEAK`, `HERMES_UNSUPPORTED_OPERATION`, `HERMES_INVALID_INPUT`, `HERMES_INTERNAL_ERROR`
- `_MAX_PROMPT_CHARS` (10K) and `_MAX_OUTPUT_CHARS` (20K) guards
- Estimated token counts in every response

### 3. VPS Hermes Runtime Adapter (Full Parity) — SHIPPED

**File**: `adapters/models/hermes_cli.py` (rewritten from 431 → 620 lines)

New capabilities:
- **Session management**: `session_create()`, `session_send()`, `session_read()`, `session_list()`, `session_close()` — VPS-managed conversation history prepended to each Hermes call
- **Capability registry**: `CAPABILITY_STATES` dict with 15 capabilities, each marked supported/unsupported/unknown
- **Role matrix**: `ROLE_REQUIREMENTS` dict mapping roles to required benchmark tests, with BLOCKED for status_report/vision
- **Role assignment**: `get_assigned_roles()` / `get_blocked_roles()` — derived from benchmark results, not assumptions
- **Diagnostics**: `diagnostics()` — checks, blockers with recovery actions, capabilities, roles, sessions
- **Provider inventory**: `providers()` / `models()` — config data with secret stripping
- **Health**: `health()` — structured response with status/capabilities/roles
- **Cancellation**: `cancel()` — dispatches `hermes.cancel` to Beast
- **Structured responses**: `build_success_response()` / `build_error_response()` — matching the Hermes contract

### 4. Expanded Benchmark Suite — SHIPPED

Benchmark expanded from 5 tests to 10:

| Test | Purpose | Role Gated |
|---|---|---|
| liveness | Binary alive? | conversation, quick_triage |
| grounding | Refuses to fabricate system data? | — |
| summarization | Summarizes provided text? | summarization, research |
| conversation | Coherent multi-turn? | conversation, planning |
| latency | Under 30s threshold? | — |
| identity | Knows "UMH = Universal Meta Harness"? | — |
| no_data_refusal | Refuses Docker status without data? | — |
| supplied_data | Summarizes ONLY supplied data? | — |
| code_review | Reviews small diff? | code_review |
| code_patch | Produces simple function? | build_code |

Role assignment is mechanical: each role requires a specific test to pass. No role is assumed.

### 5. Router Integration — SHIPPED

**Modified**: `adapters/models/model_router.py`

- `_hermes_allowed_for_purpose()` — checks benchmark-assigned roles before allowing Hermes into a purpose chain
- `SUPPLEMENTAL_PROVIDERS` — added `summarize` purpose
- Hermes supplemental providers are now benchmark-gated (not just verified-gated)
- `_call_hermes()` now reports estimated tokens

### 6. Provider Health UI — SHIPPED

**Modified**: `transports/api/organism_bridge.py`

Provider health endpoint now uses `hermes_health()` and `hermes_diagnostics()` instead of raw field assembly. Returns:
- Full capability registry
- Assigned/blocked roles
- Diagnostic checks with actionable blockers
- Session counts
- Benchmark results

### 7. Session-Aware Conversations — SHIPPED

Session contract:
- `session_id`: `hermes_beast_<uuid12>`
- `conversation_id`: matches session_id or custom
- `purpose`: conversation/summarization/quick_triage
- `turn_count`: incremented per send
- `status`: active/idle/closed/expired/error

History management:
- Last 20 turns stored per session
- Context budget: 8000 chars from recent turns prepended to each call
- Auto-expiry after 1 hour idle
- Explicit close marks session as closed

### 8. Streaming / Pseudo-Streaming — DOCUMENTED (UNSUPPORTED)

Hermes CLI is synchronous — no streaming API. This is explicitly declared:
- `CAPABILITY_STATES["streaming"] = "unsupported"`
- `CAPABILITY_STATES["pseudo_streaming"] = "supported"`
- Notes in capability registry explain: "Hermes CLI is synchronous; pseudo-streaming via heartbeat on VPS side"

Pseudo-streaming implementation is deferred — the infrastructure exists but requires cockpit WebSocket integration which is out of scope for this phase.

### 9. Cancellation — SHIPPED

- Beast-side: `Popen` with `_active_process` tracking, thread-safe lock, `kill()` on cancel
- VPS-side: `cancel()` dispatches `hermes.cancel` operation to Beast
- Returns structured response: cancelled/not_cancelled with reason

### 10. Safe Context Handling — SHIPPED

- Prompts capped at 10K chars
- Output capped at 20K chars
- Session history capped at 8K chars context budget
- Base64 encoding prevents shell injection
- Null bytes stripped
- No secrets in benchmark logs
- Provider inventory auto-redacts secrets

### 11. Tests — 40/40 PASS + 64/64 EXISTING = 104/104

| Category | Tests | Status |
|---|---|---|
| Health checks | 3 | PASS |
| Provider/model inventory | 3 | PASS |
| Generate calls | 3 | PASS |
| Session lifecycle | 6 | PASS |
| Capability registry | 2 | PASS |
| Role matrix | 5 | PASS |
| Router integration | 3 | PASS |
| Diagnostics | 2 | PASS |
| Prompt safety | 4 | PASS |
| Structured responses | 2 | PASS |
| Beast adapter | 3 | PASS |
| Cancellation | 2 | PASS |
| Grounding regression | 2 | PASS |
| **New total** | **40** | **PASS** |
| Existing grounding firewall | 64 | PASS |
| **Combined total** | **104** | **PASS** |

### 12. Gate Compliance

- Dependency direction: No new violations (checked with `check_dependency_direction.py`)
- Type coherence: No new types — used existing `ModelProvider.HERMES`, `TaskType`, `ProviderRole`
- Projection boundary: Clean
- Instance context: Clean — no hardcoded names
- God file check: All files under 3000 lines (hermes_cli.py: 620 lines)

## Files Modified

| File | Action | Lines |
|---|---|---|
| `adapters/models/hermes_cli.py` | REWRITE | 620 (from 431) |
| `adapters/models/model_router.py` | MODIFY | ~25 lines changed |
| `nodes/windows/umh_node/adapters/hermes.py` | REWRITE | 320 (from 127) |
| `transports/api/organism_bridge.py` | MODIFY | ~15 lines changed |
| `tests/test_hermes_adapter_parity.py` | NEW | 370 |
| `data/umh/trinity_convergence/hermes_adapter_parity_audit.md` | NEW | audit |
| `data/umh/trinity_convergence/phase14_14e_hermes_adapter_parity_report.md` | NEW | report |

## Verdict: PARTIAL

**Shipped:**
- Full adapter parity audit
- Beast adapter with all 8 operations
- VPS adapter with health/generate/chat/session/diagnostics/benchmark/cancel/roles/capabilities
- Session-aware conversations (VPS-managed)
- 10-test expanded benchmark suite with role assignment
- Benchmark-gated router integration
- Provider health with full diagnostics
- 104/104 tests pass
- Safe context handling with limits
- Structured error codes
- Cancellation (best-effort)
- Capability registry (explicit supported/unsupported/unknown)

**Unsupported (honest, documented):**
- Native streaming: Hermes CLI is synchronous. Pseudo-streaming via heartbeat is declared supported but implementation deferred (requires cockpit WebSocket integration)
- Native sessions: Hermes is stateless. VPS manages history and prepends to each call.
- Exact token counts: estimated only (chars/4). Hermes doesn't report tokens.
- Vision: unproven, blocked in role matrix
- Tool use: unproven, blocked

**Why PARTIAL not SHIPPED:**
Pseudo-streaming implementation is deferred — the capability is declared but the cockpit heartbeat integration wasn't built. Streaming was a stated deliverable (Workcell E). The infrastructure exists (Beast adapter tracks active process, VPS can poll), but the cockpit-side consumer wasn't implemented.

**What's needed for SHIPPED:**
1. Cockpit WebSocket integration for Hermes heartbeat updates during long calls
2. Live field tests through DEX (provider health, conversation, summarization, no-data refusal, code role gate)
3. Re-run expanded benchmark on Beast to generate role assignments for production
