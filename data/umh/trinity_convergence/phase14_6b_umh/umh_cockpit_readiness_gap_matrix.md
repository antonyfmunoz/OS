# UMH Cockpit Readiness Gap Matrix

Phase: 14.6B-UMH
Status: DRAFT
Generated: 2026-06-03

---

## Readiness Criteria Status

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Voice/text command intake | PARTIAL | `VoiceCommandBar.tsx` (413 lines) and `VoiceWaveform.tsx` (31 lines) exist. Voice store wired. Whisper/VAD in dependencies. Text input functional via `CommandPalette.tsx` (130 lines). Runtime E2E voice pipeline unverified -- no production proof of audio capture through transcription to command execution. |
| 2 | Command routing | IMPLEMENTED | `CommandPalette.tsx` handles text input. `OrchestratorKernel.classify_intent()` provides deterministic intent classification via `IntentClassifier` (168 lines, keyword/pattern matching, no LLM). Gateway routes classified intents to appropriate handlers. |
| 3 | Approval workflows | IMPLEMENTED | `ApprovalsPanel.tsx` (251 lines) with `useApprovalStore`. Approve/deny actions wired. Pending/history split. Organism store `approveEnvelope()` integration. Backend governance routes in `transports/api/http/routes/governance.ts`. Discord bridge for remote approval. |
| 4 | Work packet visibility | IMPLEMENTED | Cockpit panels render work packet state from organism API. Work unit counts (running/queued) returned by execution status endpoint. Packet lifecycle visible through approvals and execution panels. |
| 5 | Agent visibility | IMPLEMENTED | Agent registry queryable via substrate API. Agent heartbeats tracked in organism workcell protocol. Cockpit renders agent status through organism endpoints. |
| 6 | Model routing visibility | IMPLEMENTED | `adapters/models/model_router.py` exposes routing chain status. Fallback chain (cc_sdk -> Gemini -> Groq -> Ollama) observable. Provider health trackable through error recording. |
| 7 | Infrastructure visibility | IMPLEMENTED | System routes (`transports/api/http/routes/system.ts`) expose VPS health, Docker container status, service heartbeats. Organism routes expose workcell health. |
| 8 | Projection status | PARTIAL | Projection registration exists via abstract ports (`substrate/sockets/projection_port.py` planned). EOS projection active. CreatorOS/LyfeOS projections defined in config but runtime status visibility limited to what organism routes expose. |
| 9 | Execution control | STUB | `transports/api/http/routes/execution.ts` (125 lines) defines 7 endpoints: `/status`, `/log`, `/authority`, `/start`, `/stop`, `/pause`, `/resume`. Start/stop/pause/resume delegate to Python bridge but return static `{ ok: false, error }` on bridge failure. No verified production execution control loop. |
| 10 | Source truth visibility | PARTIAL | `substrate/reality_model/canonical.py` (`CanonicalRealityModel`) maintains source truth. Cockpit can query canonical state. Production truth promotion lifecycle exists but real-time diff visibility between source and production truth is not surfaced in cockpit UI. |
| 11 | Tmux visibility | PARTIAL | Tmux session architecture documented. VPS runs services in tmux. Cockpit has no live tmux pane streaming -- visibility requires SSH access. Session list queryable but output not rendered. |
| 12 | File/meta-IDE | PARTIAL | `EditorPanel.tsx` exists in cockpit. File tree rendering present. No live file editing, no git diff viewer, no integrated terminal. Meta-IDE vision documented but implementation is scaffold-level. |
| 13 | Error/log visibility | PARTIAL | `substrate/observability/error_recorder.py` centralizes error recording. Execution log endpoint (`/execution/log`) exists. Cockpit can poll logs. No real-time log streaming. No structured error dashboard in cockpit UI. |
| 14 | Security/risk | PARTIAL | Governance routes expose risk classification. `substrate/control_plane/governance.py` provides deterministic risk scoring. Auth middleware in `transports/api/http/middleware/`. No cockpit-visible security dashboard. Rate limiting and dev bypass documented but not surfaced in UI. |
| 15 | Degraded mode | NOT_IMPLEMENTED | No cockpit-level degraded mode handling. When backend services fail, cockpit shows connection errors but has no graceful degradation UI, no offline mode, no cached-state fallback rendering. |

---

## Summary

| Status | Count |
|--------|-------|
| IMPLEMENTED | 6 |
| PARTIAL | 7 |
| STUB | 1 |
| NOT_IMPLEMENTED | 1 |
| **Total** | **15** |

### Critical Gaps

1. **Execution control** -- The 7 endpoints exist but are not wired to a verified execution control loop. This is the primary gap for operator-governed autonomous execution.
2. **Degraded mode** -- No fallback UI behavior when backend is unavailable.
3. **Voice E2E** -- Components exist but runtime pipeline is unverified end-to-end.
