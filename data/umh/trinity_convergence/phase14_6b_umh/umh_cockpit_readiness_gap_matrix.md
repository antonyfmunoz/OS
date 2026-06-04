# UMH Stage 1 Organism Readiness Gap Matrix

Phase: 14.6B-UMH (revised 14.6F)
Status: RATIFIED -- all 18 P0 decisions operator-approved (2026-06-04)
Generated: 2026-06-03
Revision note: Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

---

## Stage 1 Organism Context (DEC-146C-003, RATIFIED 2026-06-04)

Gaps are evaluated against the indivisible Stage 1 organism target (Reality Model + Cockpit + Memory + Governed Execution Loop). Per DEC-146C-003 (Option B, RATIFIED 2026-06-04), each gap should be assessed by how it blocks integrated organism viability, not just isolated Cockpit or dashboard functionality. The 10 operator-specified acceptance criteria for Stage 1 minimum viability are the primary gap-closure target. Gaps in reality-model rendering through Cockpit are as critical as gaps in the reality model itself.

**Reality-Model Interface Framing (DEC-146C-001):** Each gap below is assessed not just as a missing Cockpit feature, but as a blind spot in the operator's ability to observe, command, or govern a specific reality-model layer. UMH models reality across 12 layers (physical, digital, cognitive, biological, social, economic, symbolic, operational, software, memory, source-truth, OS-level). A gap that blocks operator visibility into a reality-model layer is a Stage 1 organism gap, not merely a UI gap.

**Materialization Principle (DEC-146C-002, RATIFIED 2026-06-04):** Gaps are typed per the materialization principle -- each missing capability is classified as under-resourced, not-yet-acquired, or unproven, with an acquisition path identified. No gap is terminal.

---

## Readiness Criteria Status

| # | Criterion | Reality-Model Layer | Status | Evidence | Gap Type (DEC-146C-002) |
|---|-----------|---------------------|--------|----------|-------------------------|
| 1 | Voice/text command intake | Cognitive (operator intent) | PARTIAL | `VoiceCommandBar.tsx` (413 lines) and `VoiceWaveform.tsx` (31 lines) exist. Voice store wired. Whisper/VAD in dependencies. Text input functional via `CommandPalette.tsx` (130 lines). Runtime E2E voice pipeline unverified -- no production proof of audio capture through transcription to command execution. | Unproven -- components exist, E2E path not verified |
| 2 | Command routing | Operational (execution dispatch) | IMPLEMENTED | `CommandPalette.tsx` handles text input. `OrchestratorKernel.classify_intent()` provides deterministic intent classification via `IntentClassifier` (168 lines, keyword/pattern matching, no LLM). Gateway routes classified intents to appropriate handlers. Single unified execution path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003). | -- |
| 3 | Approval workflows | Operational (governance) | IMPLEMENTED | `ApprovalsPanel.tsx` (251 lines) with `useApprovalStore`. Approve/deny actions wired. Pending/history split. Organism store `approveEnvelope()` integration. Backend governance routes in `transports/api/http/routes/governance.ts`. Discord bridge for remote approval. | -- |
| 4 | Work packet visibility | Operational (execution state) | IMPLEMENTED | Cockpit panels render work packet state from organism API. Work unit counts (running/queued) returned by execution status endpoint. Packet lifecycle visible through approvals and execution panels. | -- |
| 5 | Agent visibility | Software (agent state) | IMPLEMENTED | Agent registry queryable via substrate API. Agent heartbeats tracked in organism workcell protocol. Cockpit renders agent status through organism endpoints. | -- |
| 6 | Model routing visibility | Digital (intelligence routing) | IMPLEMENTED | `adapters/models/model_router.py` exposes routing chain status. Fallback chain (cc_sdk -> Gemini -> Groq -> Ollama) observable. Provider health trackable through error recording. | -- |
| 7 | Infrastructure visibility | Physical + OS-level | IMPLEMENTED | System routes (`transports/api/http/routes/system.ts`) expose VPS health, Docker container status, service heartbeats. Organism routes expose workcell health. | -- |
| 8 | Projection status | Operational (instance reality models) | PARTIAL | Projection access via abstract port pattern (DEC-146B-UMH-005, RATIFIED 2026-06-04). EOS projection active. CreatorOS/LyfeOS projections defined in config but runtime status visibility limited to what organism routes expose. Each projection is an instance reality model (DEC-146C-001). | Under-resourced -- abstract port ratified, cockpit rendering not built |
| 9 | Execution control | Operational (governed execution) | STUB | `transports/api/http/routes/execution.ts` (125 lines) defines 7 endpoints: `/status`, `/log`, `/authority`, `/start`, `/stop`, `/pause`, `/resume`. Start/stop/pause/resume delegate to Python bridge but return static `{ ok: false, error }` on bridge failure. No verified production execution control loop. This directly blocks Stage 1 Governed Execution Loop (DEC-146C-003). | Under-resourced -- endpoints exist, bridge wiring needed |
| 10 | Source truth visibility | Source-truth layer | PARTIAL | `substrate/reality_model/canonical.py` (`CanonicalRealityModel`) maintains source truth (one of 12 reality-model layers, DEC-146C-001). Cockpit can query canonical state. Production truth promotion lifecycle exists but real-time diff visibility between source and production truth is not surfaced in cockpit UI. | Under-resourced -- backend exists, cockpit rendering needed |
| 11 | Tmux visibility | OS-level (process state) | PARTIAL | Tmux session architecture documented. VPS runs services in tmux. Cockpit has no live tmux pane streaming -- visibility requires SSH access. Session list queryable but output not rendered. | Under-resourced -- backend queryable, UI not built |
| 12 | File/meta-IDE | Software (source code state) | PARTIAL | `EditorPanel.tsx` exists in cockpit. File tree rendering present. No live file editing, no git diff viewer, no integrated terminal. Meta-IDE vision documented but implementation is scaffold-level. | Under-resourced -- scaffold exists, capabilities not wired |
| 13 | Error/log visibility | Operational (observability) | PARTIAL | `substrate/observability/error_recorder.py` centralizes error recording. Execution log endpoint (`/execution/log`) exists. Cockpit can poll logs. No real-time log streaming. No structured error dashboard in cockpit UI. | Under-resourced -- recording exists, streaming/UI not built |
| 14 | Security/risk | Operational (governance) | PARTIAL | Governance routes expose risk classification. `substrate/control_plane/governance.py` provides deterministic risk scoring. Auth middleware in `transports/api/http/middleware/`. No cockpit-visible security dashboard. Rate limiting and dev bypass documented but not surfaced in UI. | Under-resourced -- classification exists, dashboard not built |
| 15 | Degraded mode | All layers (fallback rendering) | NOT_IMPLEMENTED | No cockpit-level degraded mode handling. When backend services fail, cockpit shows connection errors but has no graceful degradation UI, no offline mode, no cached-state fallback rendering. Per DEC-146C-003, Cockpit without reality model is only a dashboard -- degraded mode must render last-known reality-model state. | Not-yet-acquired -- requires client-side cache + fallback rendering |

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 6 |
| PARTIAL | 7 |
| STUB | 1 |
| NOT_IMPLEMENTED | 1 |
| **Total** | **15** |

### Critical Gaps (assessed by Stage 1 organism impact)

1. **Execution control (Governed Execution Loop -- DEC-146C-003)** -- The 7 endpoints exist but are not wired to a verified execution control loop. This directly blocks the Governed Execution component of the indivisible Stage 1 organism. Gap type: under-resourced.
2. **Degraded mode (all reality-model layers)** -- No fallback UI behavior when backend is unavailable. Per DEC-146C-003, Cockpit without the reality model is only a dashboard. Degraded mode must render last-known reality-model state. Gap type: not-yet-acquired.
3. **Voice E2E (cognitive layer -- operator intent)** -- Components exist but runtime pipeline is unverified end-to-end. Gap type: unproven.
4. **Memory visibility (Memory -- DEC-146C-003)** -- Memory is one of the four indivisible Stage 1 components. No cockpit panel for memory browsing, search, or promotion. Gap type: under-resourced.
5. **Source truth visibility (source-truth layer -- DEC-146C-001)** -- Blocks operator from observing the source-truth layer of the 12-layer reality model. Gap type: under-resourced.
