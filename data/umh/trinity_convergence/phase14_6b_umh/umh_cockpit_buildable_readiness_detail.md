# UMH Stage 1 Organism Buildable Readiness Detail

Phase: 14.6B-UMH (revised 14.6F)
Status: RATIFIED -- all 18 P0 decisions operator-approved (2026-06-04)
Generated: 2026-06-03
Revision note: Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

---

## Stage 1 Organism Context (DEC-146C-003, RATIFIED 2026-06-04)

Stage 1 is one minimum viable UMH organism (DEC-146C-003, Option B, RATIFIED 2026-06-04): Reality Model + Cockpit + Memory + Governed Execution Loop. These are not separate products or sequential phases. Readiness criteria below must be evaluated in the context of the indivisible Stage 1 organism, not as isolated Cockpit capabilities. Each criterion contributes to one or more of the four organism components:

- **RM** = Reality Model component
- **CK** = Cockpit component
- **MM** = Memory component
- **GE** = Governed Execution component

Stage 1 minimum viability does not require commercial-grade completeness. It requires a partially functional integrated vertical slice (DEC-146C-003 acceptance criteria 1-10). Per the Materialization Principle (DEC-146C-002, RATIFIED 2026-06-04), gaps in capability do not invalidate Stage 1 -- they create typed gaps and acquisition paths that the organism itself can work to close.

---

## Per-Criterion Detail

### 1. Voice/Text Intake

**Classification:** PARTIALLY_IMPLEMENTED

**Components:**
- `cockpit/src/renderer/components/VoiceCommandBar.tsx` (413 lines) -- Full voice command bar with microphone toggle, audio visualization, state management
- `cockpit/src/renderer/components/VoiceWaveform.tsx` (31 lines) -- Audio waveform visualization component
- `cockpit/src/renderer/components/CommandPalette.tsx` (130 lines) -- Text command input with keyboard shortcut activation

**Store:** Voice store wired into cockpit state management. Audio capture state, transcription results, and command dispatch tracked.

**Dependencies:** Whisper (speech-to-text) and VAD (voice activity detection) listed in project dependencies.

**Gap:** Runtime E2E unverified. No production proof that audio capture -> VAD -> Whisper transcription -> command text -> intent classification -> execution works as a complete pipeline. Text path via CommandPalette is functional.

---

### 2. Command Routing

**Classification:** IMPLEMENTED

**Components:**
- `cockpit/src/renderer/components/CommandPalette.tsx` -- User-facing command entry
- `substrate/organism/intent_classifier.py` (IntentClassifier, line 168) -- Deterministic classification using keyword/pattern matching. No LLM dependency. Loads entity patterns from `data/umh/config/entity_patterns.json` with hardcoded defaults.
- `substrate/organism/orchestrator_kernel.py` -- `classify_intent()` method routes through IntentClassifier, returns `IntentClassification`
- `substrate/control_plane/runtime/gateway.py` -- Gateway class routes classified intents to appropriate execution handlers

**Flow:** CommandPalette -> OrchestratorKernel.classify_intent() -> IntentClassifier.classify() -> Gateway routing -> Handler dispatch. Execution flows through single unified path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003, RATIFIED 2026-06-04).

**Deterministic-first compliant:** Intent classification uses keyword/pattern matching as spine. No LLM required for routing.

---

### 3. Ambiguity Handling

**Classification:** PARTIALLY_IMPLEMENTED

IntentClassifier returns classification with confidence indicators. Low-confidence classifications route to clarification logic in OrchestratorKernel. No cockpit-visible disambiguation dialog -- ambiguous intents are handled server-side with fallback classification.

---

### 4. Confirmation Flows

**Classification:** IMPLEMENTED

`substrate/control_plane/governance.py` provides deterministic risk classification (LOW/MEDIUM/HIGH/CRITICAL). Actions classified above threshold require operator confirmation before execution proceeds. Confirmation integrates with approval workflow (criterion 5).

---

### 5. Approval Workflows

**Classification:** IMPLEMENTED

**Components:**
- `cockpit/src/renderer/panels/ApprovalsPanel.tsx` (251 lines)
  - `useApprovalStore` for state: `approvals`, `approve()`, `deny()`
  - Pending/history split view
  - `useOrganismStore.approveEnvelope()` for organism-level envelope approval
  - Approve/deny action buttons per pending item
- `transports/api/http/routes/governance.ts` -- Backend governance endpoints
- Discord bridge -- Remote approval via Discord reactions/commands

**Flow:** Governance classifies risk -> High-risk items enter pending queue -> Operator approve/deny via cockpit or Discord -> Execution proceeds or aborts

---

### 6. Manual Intervention

**Classification:** PARTIALLY_IMPLEMENTED

Operator can approve/deny pending work via ApprovalsPanel. Pause/resume available as scaffold endpoints. No "take over" mechanism where operator can inject manual steps mid-execution. No inline override UI during active work packet execution.

---

### 7. Pause/Resume/Abort (Execution Control)

**Classification:** SCAFFOLD

**Endpoints** (`transports/api/http/routes/execution.ts`, 125 lines):

| Endpoint | Method | Status |
|----------|--------|--------|
| `/execution/status` | GET | Returns work unit counts, risk level, approval status |
| `/execution/log` | GET | Returns execution log entries |
| `/execution/authority` | GET | Returns authority/permissions state |
| `/execution/start` | POST | Delegates to Python bridge, returns bridge result or `{ ok: false, error }` |
| `/execution/stop` | POST | Same delegation pattern |
| `/execution/pause` | POST | Same delegation pattern |
| `/execution/resume` | POST | Same delegation pattern |

All 4 mutation endpoints (start/stop/pause/resume) delegate to Python bridge via `callPythonBridge()`. On bridge failure, return `{ ok: false, error }`. No verified production execution control cycle exists -- the bridge target functions need runtime verification.

---

### 8. Work Packet Visibility

**Classification:** IMPLEMENTED

Execution status endpoint returns structured work unit state:
- Running count, queued count
- Risk level per execution context
- Approval status
- Organism routes expose full work packet lifecycle through workcell protocol

Cockpit panels consume these endpoints and render work packet state.

---

### 9. Agent Visibility

**Classification:** IMPLEMENTED

Agent registry queryable via substrate API. Organism workcell protocol tracks agent heartbeats (`data/umh/organism/workcells/*/heartbeat.json` for advisor, executor, researcher, reviewer). Cockpit renders agent status from organism endpoints.

---

### 10. Model Routing Visibility

**Classification:** IMPLEMENTED

`adapters/models/model_router.py` exposes the full routing chain. `call_with_fallback()` logs provider selection, fallback events, and response quality. Error recorder centralizes failures. Current chain: cc_sdk -> Gemini 2.5 Flash -> Groq -> Ollama.

---

### 11. Tool Call Visibility

**Classification:** PARTIALLY_IMPLEMENTED

Execution spine (`substrate/execution/spine.py`) traces tool invocations through the 8-stage pipeline. `substrate/execution/trace.py` records traces with Neon persistence. No dedicated cockpit panel streams tool calls in real time. Tool call history accessible via execution log endpoint.

---

### 12. Tmux/Session Visibility

**Classification:** PARTIALLY_IMPLEMENTED

VPS runs services in tmux sessions. System routes can list active sessions. No cockpit component renders live tmux output. Operator must SSH for actual session content. Session names and status queryable but output streaming not implemented.

---

### 13. VPS/Windows Visibility

**Classification:** PARTIALLY_IMPLEMENTED

System routes expose VPS metrics (health, disk, memory, container status). Windows Beast daemon (`nodes/`) connects via Tailscale node mesh on :8094. No unified cross-node dashboard in cockpit combining VPS and Windows status.

---

### 14. File/Meta-IDE Visibility

**Classification:** PARTIALLY_IMPLEMENTED

`EditorPanel.tsx` exists in cockpit. File tree rendering present. UMH IDE vision documented at `project_umh_ide.md` (end-state: forked VS Code embedded in cockpit). Current state: no live file editing, no git integration, no integrated terminal, no code intelligence.

---

### 15. Diff/Source Mutation Visibility

**Classification:** SCAFFOLD

No cockpit component renders git diffs or file mutations. Audit events in `execution_journal.jsonl` log changes at the metadata level. No visual diff viewer. No real-time file change notification in UI.

---

### 16. Infrastructure Visibility

**Classification:** IMPLEMENTED

`transports/api/http/routes/system.ts` exposes: Docker container status, service heartbeat, disk/memory/CPU metrics. Organism routes expose workcell heartbeats. Container names (os-discord, os-operator, os-webhook, os-scraper) queryable.

---

### 17. Projection Status Visibility

**Classification:** PARTIALLY_IMPLEMENTED
**Organism Component:** RM + CK

EOS projection active and queryable. CreatorOS and LyfeOS projections defined in configuration. No cockpit panel showing per-projection health dashboard, active users, or projection-specific metrics. Projection access uses abstract port pattern via substrate/sockets/projection_port.py (DEC-146B-UMH-005, RATIFIED 2026-06-04). Each projection is an instance reality model (DEC-146C-001) -- Cockpit must render per-projection reality-model state.

---

### 18. Source Truth Visibility (Reality Model: source-truth layer)

**Classification:** PARTIALLY_IMPLEMENTED
**Organism Component:** RM + CK

`substrate/reality_model/canonical.py` (`CanonicalRealityModel`) maintains source truth -- one of the 12 reality-model layers (DEC-146C-001). Queryable via substrate API. `data/umh/reality_model/canonical.json` stores current canonical state. No cockpit UI showing source truth entries or source-vs-production truth comparison. This gap blocks the operator from observing the source-truth layer of the reality model through Cockpit (violating indivisible Stage 1 per DEC-146C-003).

---

### 19. Production Truth Visibility (Reality Model: source-truth layer)

**Classification:** PARTIALLY_IMPLEMENTED
**Organism Component:** RM + CK

Production truth promotion lifecycle documented (`umh_source_truth_production_truth_lifecycle.md`). Three reality model tiers (canonical, instance, simulation). No cockpit real-time dashboard for production truth state or promotion history. Per the Materialization Principle (DEC-146C-002), this gap type is "under-resourced" -- the concept exists, the lifecycle is defined, implementation needs cockpit rendering.

---

### 20. Audit/Event Visibility

**Classification:** PARTIALLY_IMPLEMENTED

Audit trail files: `data/umh/organism/execution_journal.jsonl`, `events.jsonl`, `reports.jsonl`, `messages.jsonl`. Rich event data persisted. No cockpit panel for browsing, filtering, or searching audit events.

---

### 21. Memory Visibility (Reality Model: memory layer)

**Classification:** PARTIALLY_IMPLEMENTED
**Organism Component:** MM + CK

ConversationMemory and AgentMemory fully queryable. Semantic search via embeddings. MemoryPromoter handles promotion. No cockpit panel for memory browsing, semantic search UI, or promotion status visualization. Memory is one of the four indivisible Stage 1 components (DEC-146C-003) -- this gap directly blocks Stage 1 organism viability.

---

### 22. Error/Log Visibility

**Classification:** PARTIALLY_IMPLEMENTED

`substrate/observability/error_recorder.py` centralizes error recording (single source of truth). Execution log endpoint (`/execution/log`) returns log entries. No real-time log streaming (WebSocket/SSE). No structured error dashboard with filtering, severity, or trending.

---

### 23. Recovery/Rollback Visibility

**Classification:** MISSING
**Organism Component:** GE + CK

No cockpit mechanism for viewing execution outcome history with rollback capability. No undo/revert UI. No snapshot-based recovery. Execution outcomes are recorded but not reversible through the cockpit. Per the Materialization Principle (DEC-146C-002), this gap is typed as "not-yet-acquired" capability with a clear acquisition path: execution journal already captures outcomes, rollback requires adding reversibility metadata and a cockpit rendering surface.

---

### 24. Security/Risk Visibility

**Classification:** PARTIALLY_IMPLEMENTED

Governance provides deterministic risk classification (LOW/MEDIUM/HIGH/CRITICAL). Auth middleware in `transports/api/http/middleware/`. Risk levels assigned per work packet. No cockpit security dashboard showing: risk distribution, auth event log, rate limit status, or active session audit.

---

### 25. Degraded-Mode Operation

**Classification:** MISSING
**Organism Component:** CK + RM

No cockpit fallback behavior when backend services are unavailable. No offline mode. No cached-state rendering for last-known-good state. No graceful degradation UI that communicates reduced capability. When the API is unreachable, cockpit shows connection errors with no useful fallback. Per indivisible Stage 1 (DEC-146C-003), Cockpit without the reality model is only a dashboard -- but degraded mode should still render last-known reality-model state rather than showing nothing.
