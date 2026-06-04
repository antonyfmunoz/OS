# UMH Observability, Logging, and Audit Map

Phase: 14.6B-UMH | Status: DRAFT | Provenance: CODE_RESOLVED_CURRENT_TRUTH

---

## Error Recording

### Fix-Forever Pattern (substrate/observability/error_recorder.py, 58 lines)
- record_error(component, error_msg, context_dict)
- Writes to logs/errors.jsonl with timestamp, component, error, context
- JSONL format with rotation (substrate/observability/jsonl_rotation.py)
- Called throughout substrate (spine, memory, trace, organism)
- Centralized -- single source of truth for all errors

## Trace Recording

### Execution Traces (substrate/execution/trace.py, 126 lines)
- ConcreteTraceRecorder -- in-memory store + Neon persistence
- TraceRecord with TraceEvents (18 event types)
- Events: SIGNAL_RECEIVED, IDENTITY_RESOLVED, CONTEXT_ASSEMBLED, GOVERNANCE_DECIDED, MEMORY_RECALLED, PLAN_COMPOSED, ADAPTER_CALLED, ADAPTER_RESPONDED, EXECUTION_COMPLETED, FEEDBACK_CAPTURED, ERROR, CUSTOM, etc.
- Served via /api/umh/tasks endpoint (recent 100 traces)
- Served via /api/umh/analytics endpoint (model usage, daily traces, error rate)

## Memory Logging

### Conversation Memory (substrate/state/memory/memory.py)
- Stores both user input and assistant output per session
- Neon-backed with session_id, role, content, channel, agent metadata
- Queryable via /api/umh/memory endpoint

### Canonical Memory Store
- Promoted observations (substrate/state/memory/contracts/canonical_memory_store_v1.py)
- Served via /api/umh/observations endpoint
- Proofs at data/runtime/canonical_memory_store/proofs/

## Organism Event Spine

### Event System (substrate/organism/event_spine.py)
- EventDomain, EventPriority enums
- Organism-internal event bus for coordination
- Events visible via cockpit organism routes

## Audit Capabilities

### What IS Audited
1. Execution traces with 18 event types (every pipeline execution)
2. Errors with component + context (fix-forever pattern)
3. Conversation turns (both sides stored to Neon)
4. Governance decisions (approval/deny recorded)
5. Organism work packets and deliverables
6. Approval history (file-based pending/approved)

### What IS NOT Audited
1. Raw API requests/responses (no request logging middleware)
2. Who accessed which endpoint (no access log)
3. Config changes (runtime changes not persisted)
4. Secret access (no secret access logging)
5. Cross-projection data access (no data access audit)
6. File system changes (no file access audit)
7. Database queries (no query logging beyond trace events)

## Cockpit Visibility

### Panels with Observability
- ActivityPanel -- unified event feed (traces + comms + approvals + deliverables)
- AnalyticsPanel -- model usage, daily traces, error rate
- EventConsole -- real-time event console component

### API Endpoints
- GET /api/umh/activity/stream -- unified feed
- GET /api/umh/analytics -- model usage stats
- GET /api/umh/tasks -- recent 100 traces
- WS /api/umh/ws -- live pulse (2s interval: CPU, memory, disk, active agents, pending tasks/approvals)

## Log Files

### Primary Logs
- logs/errors.jsonl -- centralized error recording
- JSONL rotation for large files
- Docker container logs (stdout/stderr)

### Data Store Logs
- data/umh/organism/events.jsonl -- organism events
- data/umh/organism/execution_journal.jsonl -- execution journal
- data/umh/organism/messages.jsonl -- organism messages
- data/umh/organism/reports.jsonl -- organism reports

## Gaps

1. **P0**: No request/access logging on cockpit API -- cannot audit who did what
2. **P1**: No structured log aggregation (everything in JSONL files)
3. **P1**: No alerting system (errors recorded but not alerted on)
4. **P1**: No log retention policy (files grow unbounded)
5. **P2**: No distributed tracing (no correlation across services)
6. **P2**: No metrics collection (no Prometheus/StatsD/etc.)
7. **P2**: No centralized log viewer (no ELK/Loki/etc.)
8. **P3**: OTEL exporters disabled (OTEL_*_EXPORTER=none in docker-compose)
