# Session D — Discovery Report
## Trace + Memory + Workstation State

**Date**: 2026-05-18
**Session**: D (parallel build)
**Target**: services/jarvis/

---

## 1. Existing Memory Systems

### Canonical Memory Store (JSONL append-only)
- **Path**: `data/runtime/canonical_memory_store/`
- **Contract**: `state/memory/contracts/canonical_memory_store_v1.py`
- **Key class**: `CanonicalMemoryStore` — promote_candidate(), _update_index()
- **Format**: JSONL (memories.jsonl) + JSON index (index.json) + promotion_receipts.jsonl
- **Entry schema**: MemoryEntry dataclass — memory_id, candidate_id, memory_type, primitive_type, label, content, confidence, source_document_id, etc.
- **Promotion schema**: PromotionReceipt — receipt_id, candidate_id, decision (PROMOTED|REJECTED|DEFERRED), reason, confidence, promoter, timestamp

### Agent Memory (Neon PostgreSQL)
- **Path**: `state/memory/memory.py`
- **Connection**: `state.storage.db.get_conn()` — RLS-scoped with SET LOCAL app.current_org_id
- **Tables**: interactions, outcomes, events, human_profiles, embeddings
- **Interface**: `AgentMemory.log()` → returns interaction_id (UUID)

### SQLite Fallback Stores
- `data/runtime/memory.sqlite` — event_bus, gateway, human_intelligence
- `data/runtime/approvals.sqlite` — approval tracking
- `data/runtime/identities.sqlite` — identity management
- `data/runtime/tasks.sqlite` — task tracking

### Ingestion Candidates
- `data/runtime/w0_ingestion_candidates/` — preliminary candidates
- `data/runtime/w0_memory_governance/` — governance records
- `data/runtime/real_ingestion_candidates/` — ingestion-phase candidates

**DECISION**: Jarvis MemoryCandidate is a NEW staging layer. It does NOT write to canonical memory. It produces candidates that could later be promoted via CanonicalMemoryStore.promote_candidate(). This respects the existing promotion governance contract.

---

## 2. Existing Trace/Log Systems

### Core Observability
- **Contract**: `core/observability.py` — Observability class, LogPaths dataclass
- **Log paths** (data/):
  - workflow_log.jsonl, orchestrator_log.jsonl, harness_log.jsonl
  - action_log.jsonl, persistent_agents_log.jsonl
  - optimizer_proposals.jsonl, advisor_log.jsonl
- **Text logs** (logs/):
  - audit.log, bash_commands.log, cc_auth_health.log
  - event_spine.jsonl, interaction_archive.jsonl
- **Decision/execution logs** (logs/decisions/, logs/execution/, logs/idempotency/)

### Proof Artifact Directories
- `data/runtime/canonical_memory_store/proofs/` — timestamped proof directories
- `data/runtime/sync_proofs/` — 159 MB sync verification
- `data/runtime/execution_authority_proofs/` — execution validation
- `data/runtime/live_execution_proofs/` — live exec proofs

**DECISION**: Jarvis traces are a separate concern from existing observability logs. They live in `data/jarvis/traces/` (JSONL) and `data/jarvis/proofs/` (JSON artifacts). No overlap with existing log paths.

---

## 3. Database Conventions

- **Primary**: Neon PostgreSQL via psycopg2, RLS-scoped
- **Connection**: `state.storage.db.get_conn()` context manager
- **Pattern**: RealDictCursor, SET LOCAL for org scoping
- **Fallback**: SQLite for local-first persistence
- **File-backed**: JSONL for append-only streams, JSON for indexes/state

**DECISION**: Jarvis uses file-backed JSON/JSONL as MVP. No DB dependency. This matches the existing pattern for observability (JSONL) and state (JSON).

---

## 4. Session/Resume State

- **Path**: `state/session/session_state.py`
- **Interface**: SessionState.save(), .load(), .get_resume_context(), .get_ambient(), .update_progress()
- **State file**: `state/session/session_state.json`
- **Fields**: timestamp, phase, last_completed, in_progress, files_modified, next_steps, context

**DECISION**: Jarvis WorkstationState is complementary — it tracks traces and workstation mode, not build phase. Different concern, different file. Jarvis state lives in `data/jarvis/workstation_state/`.

---

## 5. Workstation Patterns

- **Location**: `core/workstation/` — relay transport + report generators
- **Relay data**: `data/runtime/workstation_relay/` — 14 subdirectories
- **Workstation state**: `data/runtime/workstation_state/`
- **Workstation observability**: `data/runtime/workstation_observability/`

**DECISION**: Jarvis WorkstationProfile is a lightweight runtime snapshot, not a relay/transport system. It reads environment state and recent traces to produce a resume context.

---

## 6. Protected Files (DO NOT MODIFY)

Per CLAUDE.md and core/environment.py FORBIDDEN_WRITE_PREFIXES:
- All data/*.jsonl log files
- runtime/, core/, scripts/, services/ (existing files)
- state/memory/memory.py (AgentMemory — explicit rule)

**DECISION**: Jarvis creates NEW files only. All new code goes in `services/jarvis/` (new directory). All new data goes in `data/jarvis/` (new directory). Zero overlap with protected paths.

---

## 7. Services Structure

Existing services are flat Python files in `services/`. No subdirectory-based service pattern exists yet.

**DECISION**: Jarvis is the first subdirectory service (`services/jarvis/`). This is forward-looking but doesn't break existing patterns. The __init__.py makes it importable as a package.

---

## 8. Integration Points

| System | How Jarvis Connects |
|--------|-------------------|
| CanonicalMemoryStore | MemoryCandidate.promotion_status tracks; does NOT call promote_candidate() |
| Observability | Jarvis has its own traces; could feed into Observability.snapshot() later |
| SessionState | Jarvis ResumeState complements, does not replace |
| model_router | Jarvis does not call LLMs directly in MVP |
| core/environment | Jarvis reads environment for WorkstationProfile |

---

## 9. Architecture Decisions

1. **Append-only JSONL** for traces (matches existing log conventions)
2. **JSON files** for proof artifacts and state snapshots (matches existing proof patterns)
3. **No DB dependency** — file-backed MVP, DB-upgradeable later
4. **Separate data directory** — `data/jarvis/` keeps Jarvis data isolated
5. **No canonical memory writes** — MemoryCandidate stages only, promotion is external
6. **Dataclass-based** models — matches existing codebase style (MemoryEntry, PromotionReceipt, etc.)
7. **Deterministic IDs** — SHA256-based, matching CanonicalMemoryStore._deterministic_id() pattern
