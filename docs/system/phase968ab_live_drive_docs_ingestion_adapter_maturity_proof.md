# Phase 96.8AB — Live Drive/Docs Ingestion Adapter Maturity Proof

## What This Proves

This phase matures the substrate from abstract adapter packages
(metadata, governance lists, maturity percentages) to concrete
execution-level adapters that can open, extract, normalize,
and ingest content from a configured safe Google Doc through the
full governed pipeline.

## Adapter Maturity

### Google Drive Adapter v1 (`core/adapters/google_drive_adapter_v1.py`)
- Safe URL validation — only configured target accepted
- Arbitrary URLs, empty URLs, non-Drive URLs all blocked
- Drive open proof generation with trace linkage
- Bounded metadata read for known safe documents
- Full governance constraint set (no mutation, no broad search,
  no secrets capture, no autonomous recursive ingestion)
- Status tracking through full lifecycle

### Google Docs Adapter v1 (`core/adapters/google_docs_adapter_v1.py`)
- Safe document targeting — only configured doc accepted
- Dual extraction paths: Computer Use (CU) and API
- CU/API independently enableable/disableable
- Bounded preview generation (configurable char limit)
- Deterministic text normalization
- Content hashing for integrity verification
- Full governance constraint set

### Capability Types Registered
- `GOOGLE_DRIVE_SAFE_OPEN`
- `GOOGLE_DOCS_SAFE_OPEN`
- `GOOGLE_DOCS_SAFE_EXTRACT`
- `GOOGLE_DOCS_CU_EXTRACT`
- `GOOGLE_DOCS_API_EXTRACT`

## CU / API Parity

### Parity Validator (`core/adapters/cu_api_parity_v1.py`)
- Field-by-field comparison: title, char count, word count,
  preview, normalized hash, normalized char count
- Confidence-degradation model: EXACT → HIGH → MEDIUM → LOW → NO_PARITY
- CU/OCR is NEVER treated as identical to API without confidence downgrade
- Discrepancy capture on every failing check
- Forbidden: arbitrary doc comparison, Drive-wide scan,
  silent fallback, mutation

### Parity Confidence Model
- EXACT (1.0 match + hash match): both paths produce identical output
- HIGH (≥0.8 match + hash match): minor field differences
- MEDIUM (≥0.6 match): significant but recoverable divergence
- LOW (≥0.3 match): major divergence, CU unreliable
- NO_PARITY (<0.3 match): extraction paths incomparable

## Autonomous Worker Supervision

### Worker Supervisor (`core/runtime/worker_supervisor_v1.py`)
- Six worker types: daemon, Discord, relay, Drive, Docs, Chrome
- Dependency DAG: daemon → relay → Chrome → Drive/Docs adapters
- Health checks with heartbeat and connectivity validation
- Startup plans with autostart/block/escalation decisions
- Recovery with structured remediation

### Autostart Policy
- Daemon + Discord: auto-startable
- Chrome + Windows Relay: requires human visual confirmation
- Drive + Docs adapters: blocked until Chrome healthy
- Autostart globally disableable via config

### Founder Interaction Model
The founder does NOT need to:
- Switch terminals manually
- Restart adapters manually
- Invoke relay scripts manually
- Trigger local workers manually

The founder DOES need to:
- Visually confirm Chrome launch (governance requirement)
- Visually confirm Windows Relay connectivity

## Live End-to-End Ingestion Pipeline

### Pipeline (`core/adapters/live_drive_docs_ingestion_pipeline_v1.py`)
Full chain:
1. Worker supervision → health + startup plans
2. Drive open → safe URL proof
3. Docs open → safe doc proof
4. CU extraction (if enabled) → bounded content
5. API extraction → bounded content
6. Parity check (if both paths active) → confidence score
7. Normalization → deterministic normalized content
8. Primitive decomposition → structural analysis
9. Ingestion candidate → candidate with hash + confidence
10. Memory candidate → awaiting governance
11. Governance receipt → auto-promotion BLOCKED
12. Replay query → deterministic lineage reconstruction

### Transformation Snapshots (12 types)
Every stage produces a PipelineSnapshot with:
- state_id, trace_id, parent_state_id
- transition_stage
- deterministic_content_hash
- lineage_refs (last 3 ancestors)
- governance_state
- replay_refs
- runtime_id, adapter_id
- allowed_next_actions, blocked_next_actions
- full payload

### Dual Persistence
1. Snapshots: individual JSON files per stage
2. Ledger records: hash-linked chain in TransformationStateLedger

## Deterministic Replay

- Replay query reconstructs full lineage from ledger
- All content hashes are deterministic (SHA-256)
- Hash chain is immutable — no mutation after creation
- Lineage reconstruction walks parent_state_id chain
- Trace ID groups all records for single pipeline run

## Governance Boundaries

### This phase MAY:
- Open configured safe doc
- Perform bounded extraction
- Create normalized ingestion candidates
- Create memory candidates
- Persist replay artifacts
- Perform deterministic replay

### This phase may NOT:
- Perform broad Drive ingestion
- Mutate Drive/Docs
- Auto-promote canonical truth
- Mutate world model
- Invoke execution planning
- Recursively ingest
- Perform autonomous financial actions

## What Was Real vs Simulated

### Real (proven by tests)
- Adapter initialization and configuration
- URL/document validation and blocking
- Dual extraction path (CU + API) with content processing
- Deterministic normalization
- Content hashing and integrity verification
- CU/API parity comparison with confidence scoring
- Worker dependency DAG and startup planning
- Full pipeline orchestration through all 12 stages
- Snapshot persistence to disk
- Ledger record creation and lineage reconstruction
- Governance boundary enforcement (auto-promotion blocked)
- Replay determinism and immutability

### Not Yet Real (requires live execution)
- Actual Chrome process detection
- Real Google Drive page loading
- Real Google Docs content extraction via browser
- Real CU vs API content comparison on live document
- Windows Relay connectivity to real local runtime
- Discord command triggering the pipeline

## What Remains Unproven

1. One Discord command triggering full pipeline (integration wiring)
2. Real Chrome execution on Windows desktop
3. Real Google API OAuth token refresh
4. Real CU extraction via browser automation
5. Worker autostart on real processes (not just state machines)
6. Network latency impact on extraction timeouts
7. GWS Document Scanner (22/24 docs) integration with this pipeline

## Test Coverage

- 103 focused tests across 4 test files
- All governance boundaries verified structurally
- All forbidden actions verified
- Parity confidence model verified at all levels
- Worker dependency DAG verified
- Full pipeline end-to-end verified
- Snapshot and ledger persistence verified
- Replay determinism verified

## Files

### New Modules
- `core/adapters/google_drive_adapter_v1.py`
- `core/adapters/google_docs_adapter_v1.py`
- `core/adapters/cu_api_parity_v1.py`
- `core/runtime/worker_supervisor_v1.py`
- `core/adapters/live_drive_docs_ingestion_pipeline_v1.py`

### Configuration
- `config/w0_live_drive_docs_ingestion_adapter_maturity_v1.json`

### Tests
- `tests/test_google_drive_docs_adapters_v1.py`
- `tests/test_cu_api_parity_v1.py`
- `tests/test_worker_supervisor_v1.py`
- `tests/test_live_drive_docs_ingestion_pipeline.py`

### Proof Report
- `docs/system/phase968ab_live_drive_docs_ingestion_adapter_maturity_proof.md`

## Next Gate

W0_EXECUTION_AUTHORITY_ENGINE_PROOF
