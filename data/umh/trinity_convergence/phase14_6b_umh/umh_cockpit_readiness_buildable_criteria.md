# UMH Stage 1 Organism Readiness Buildable Criteria

Phase: 14.6B-UMH (revised 14.6F)
Status: RATIFIED -- all 18 P0 decisions operator-approved (2026-06-04)
Generated: 2026-06-03
Revision note: Revised in Phase 14.6F to align with 18 ratified P0 decisions (2026-06-04).

**Stage 1 Organism Context (DEC-146C-003, RATIFIED 2026-06-04):** These 25 criteria must be evaluated as components of the indivisible Stage 1 organism (Reality Model + Cockpit + Memory + Governed Execution Loop), not as isolated Cockpit-only capabilities. Stage 1 does not require commercial-grade completeness -- it requires a partially functional integrated vertical slice. Each criterion serves one or more organism components. The 10 operator-specified Stage 1 acceptance criteria (DEC-146C-003) are the primary readiness gate; these 25 technical criteria support them. Per the Materialization Principle (DEC-146C-002, RATIFIED 2026-06-04), gaps in criteria are typed (under-resourced, not-yet-acquired, unproven) -- not terminal. Product name: "Universal Meta Harness" (DEC-146B-UMH-001, RATIFIED 2026-06-04).

---

## Classification Key

| Classification | Meaning |
|----------------|---------|
| IMPLEMENTED | Code exists, wired, verified functional |
| PARTIALLY_IMPLEMENTED | Core logic exists but incomplete or unverified paths |
| SCAFFOLD | UI component or route exists but returns static/mock data |
| DOCS_ONLY | Documented in specs but no implementation |
| MISSING | Not documented, not implemented |
| RUNTIME_VERIFICATION_REQUIRED | Code exists but needs E2E runtime proof |
| OPERATOR_DECISION_REQUIRED | Implementation approach needs operator input |

---

## 25 Readiness Criteria

### Command Layer (1-6)

| # | Criterion | Classification | Notes |
|---|-----------|----------------|-------|
| 1 | Voice/text intake | PARTIALLY_IMPLEMENTED | VoiceCommandBar (413 LOC), VoiceWaveform (31 LOC), CommandPalette (130 LOC) exist. Voice store wired. Text input works. Voice audio capture -> Whisper -> command path is RUNTIME_VERIFICATION_REQUIRED. |
| 2 | Command routing | IMPLEMENTED | CommandPalette dispatches to OrchestratorKernel. IntentClassifier provides deterministic keyword/pattern classification. Gateway routes to handlers. Single unified execution path: Substrate -> SignalRouter -> Spine (DEC-146B-UMH-003). |
| 3 | Ambiguity handling | PARTIALLY_IMPLEMENTED | IntentClassifier returns classification confidence. Low-confidence intents route to clarification. No cockpit-visible disambiguation UI. |
| 4 | Confirmation flows | IMPLEMENTED | Governance risk classification gates high-risk actions. Approval workflow requires operator confirmation before execution. |
| 5 | Approval workflows | IMPLEMENTED | ApprovalsPanel (251 LOC) with approve/deny. approvalStore state management. Organism envelope approval. Discord bridge for remote approval. Backend governance routes. |
| 6 | Manual intervention | PARTIALLY_IMPLEMENTED | Operator can approve/deny/pause through cockpit approvals. No inline manual override during mid-execution. No "take over" mechanism. |

### Execution Layer (7-9)

| # | Criterion | Classification | Notes |
|---|-----------|----------------|-------|
| 7 | Pause/resume/abort | SCAFFOLD | execution.ts routes: `/pause`, `/resume`, `/stop` exist (3 of 7 endpoints). Delegate to Python bridge. Return `{ ok: false, error }` on bridge failure. No verified production pause/resume cycle. |
| 8 | Work packet visibility | IMPLEMENTED | Execution status endpoint returns work unit counts (running/queued). Organism routes expose work packet lifecycle. Cockpit panels render state. |
| 9 | Agent visibility | IMPLEMENTED | Agent registry via substrate API. Workcell heartbeats in organism protocol. Cockpit consumes organism endpoints for agent status. |

### Observability Layer (10-18)

| # | Criterion | Classification | Notes |
|---|-----------|----------------|-------|
| 10 | Model routing visibility | IMPLEMENTED | model_router.py fallback chain observable. Provider health via error_recorder. Route selection logged per call. |
| 11 | Tool call visibility | PARTIALLY_IMPLEMENTED | Execution spine traces tool invocations. trace.py records execution traces to Neon. No cockpit panel dedicated to real-time tool call streaming. |
| 12 | Tmux/session visibility | PARTIALLY_IMPLEMENTED | Tmux sessions documented. Session list queryable via system routes. No live tmux pane rendering in cockpit. SSH required for actual output. |
| 13 | VPS/Windows visibility | PARTIALLY_IMPLEMENTED | System routes expose VPS health. Windows daemon (nodes/) connects via node mesh. No unified cross-node dashboard in cockpit. |
| 14 | File/meta-IDE visibility | PARTIALLY_IMPLEMENTED | EditorPanel exists. File tree rendering present. No live editing, no git integration, no terminal. Meta-IDE vision is documented (project_umh_ide.md). |
| 15 | Diff/source mutation visibility | SCAFFOLD | No cockpit component renders git diffs or file mutations in real time. Audit events log changes but no visual diff viewer. |
| 16 | Infrastructure visibility | IMPLEMENTED | system.ts routes: container status, service health, disk/memory. Organism routes: workcell heartbeats. Docker container names queryable. |
| 17 | Projection status visibility | PARTIALLY_IMPLEMENTED | EOS projection active and queryable. CreatorOS/LyfeOS defined in config. No cockpit panel showing per-projection health/status dashboard. Projection access via abstract port (DEC-146B-UMH-005). Each projection is an instance reality model (DEC-146C-001). |
| 18 | Source truth visibility | PARTIALLY_IMPLEMENTED | CanonicalRealityModel maintains source truth (reality-model source-truth layer, DEC-146C-001). Queryable via API. No cockpit UI showing source-vs-production truth diff. |

### Trust Layer (19-22)

| # | Criterion | Classification | Notes |
|---|-----------|----------------|-------|
| 19 | Production truth visibility | PARTIALLY_IMPLEMENTED | Production truth promotion lifecycle exists (source_truth_production_truth_lifecycle.md). Canonical vs instance reality models. No cockpit real-time production truth dashboard. |
| 20 | Audit/event visibility | PARTIALLY_IMPLEMENTED | execution_journal.jsonl, events.jsonl capture audit trail. Organism reports.jsonl. No cockpit panel for browsing/filtering audit events. |
| 21 | Memory visibility | PARTIALLY_IMPLEMENTED | ConversationMemory and AgentMemory queryable. Semantic search available. No cockpit panel for memory browsing, search, or promotion status. Memory is indivisible Stage 1 component (DEC-146C-003). |
| 22 | Error/log visibility | PARTIALLY_IMPLEMENTED | error_recorder.py centralizes errors. Execution log endpoint exists. No real-time log streaming. No structured error dashboard. |

### Resilience Layer (23-25)

| # | Criterion | Classification | Notes |
|---|-----------|----------------|-------|
| 23 | Recovery/rollback visibility | MISSING | No cockpit mechanism for viewing or triggering rollback of execution outcomes. No undo/revert UI. Gap typed as "not-yet-acquired" per Materialization Principle (DEC-146C-002). |
| 24 | Security/risk visibility | PARTIALLY_IMPLEMENTED | Governance risk classification (LOW/MEDIUM/HIGH/CRITICAL) implemented. Auth middleware active. No cockpit security dashboard showing risk distribution or auth events. |
| 25 | Degraded-mode operation | MISSING | No cockpit fallback when backend unavailable. No offline mode. No cached-state rendering. No graceful degradation UI. Cockpit without reality model is only a dashboard (DEC-146C-003) -- degraded mode must render last-known reality-model state. |

---

## Summary by Classification

| Classification | Count | Criteria |
|----------------|-------|----------|
| IMPLEMENTED | 7 | 2, 4, 5, 8, 9, 10, 16 |
| PARTIALLY_IMPLEMENTED | 13 | 1, 3, 6, 11, 12, 13, 14, 17, 18, 19, 20, 21, 22, 24 |
| SCAFFOLD | 2 | 7, 15 |
| DOCS_ONLY | 0 | -- |
| MISSING | 2 | 23, 25 |
| RUNTIME_VERIFICATION_REQUIRED | 1 | (voice E2E, counted under #1) |
| OPERATOR_DECISION_REQUIRED | 0 | -- |
| **Total** | **25** | |
