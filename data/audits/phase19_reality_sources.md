# Phase 19 — Reality Source Inventory

Every place in UMH where reality can currently change.

## Reality Write Paths

| # | Source System | File | Writes to InstanceRealityModel? | Storage | Gap |
|---|---|---|---|---|---|
| 1 | Execution (organism loop stage 6) | `substrate/organism/organism_loop.py` L278 | YES via `CanonicalWritePath` | `data/umh/reality_model/instance.jsonl` | None |
| 2 | Governance decisions | `substrate/organism/organism_loop.py` L191-227 | NO | EventSpine only | Decisions not recorded as observations |
| 3 | Claude memory sync | `substrate/memory/claude_bridge.py` L156 | NO | `data/umh/promoted_memories.json` + Neon | Missing reality bridge |
| 4 | Memory watcher | `substrate/memory/watcher.py` L187 | NO | `data/umh/promoted_memories.json` + Neon | Missing reality bridge |
| 5 | Cockpit REST POST | `transports/api/cockpit_reality_model_routes.py` | YES (ungoverned) | `data/umh/reality_model/instance.jsonl` | No source validation |
| 6 | Cockpit self-improvement | `transports/api/cockpit_self_improvement_routes.py` L216 | YES (ungoverned) | `data/umh/reality_model/instance.jsonl` | No source validation |
| 7 | IntentReceipts | `substrate/operator/intent_receipt.py` | NO (by design) | `data/umh/operator/intent_receipts.jsonl` | No gap — audit only |

## Source Detail

### 1. Execution Path (governed)
- **Owner:** `CanonicalWritePath` (`substrate/memory/canonical_write.py`)
- **Storage:** `data/umh/reality_model/instance.jsonl` (append-only JSONL)
- **Write mechanism:** `InstanceRealityModel.record(observation)`
- **Confidence:** 0.7 (success) or 0.4 (partial); exponential decay 14-day half-life
- **Timestamp:** `observed_at` from `InstanceObservation` (UTC)
- **Source attribution:** `source_trace_id` (UUID), `metadata.candidate_id`, `metadata.work_packet_id`, `metadata.proof_status`
- **Flow:** `ExecutionBundle` → `MemoryCandidateGenerator.generate_from_trace()` → `MemoryPromoter.evaluate()` → (if promoted) `InstanceRealityModel.record()`

### 2. Governance Decisions (ungoverned — gap)
- **Owner:** `PolicyEngine` (`substrate/governance/policy_engine.py`)
- **Storage:** `OrganismLoopResult.governance_decision_id` + `EventSpine` event
- **Write mechanism:** None to reality model — decision stored in result object and emitted as event
- **Confidence:** N/A (not written as observation)
- **Timestamp:** Event timestamp only
- **Source attribution:** `verdict.id` in result, `correlation_id` in event
- **Gap:** Approval/denial decisions are facts about reality but never become InstanceObservations

### 3. Claude Memory Sync (partially governed — gap)
- **Owner:** `ClaudeMemoryBridge` (`substrate/memory/claude_bridge.py`)
- **Storage:** `data/umh/promoted_memories.json` + `CanonicalMemoryStore` (Neon)
- **Write mechanism:** `MemoryPromoter.evaluate()` → `AutoReconciler.reconcile_promoted()` → `CanonicalMemoryStore`
- **Confidence:** Type-based (0.75-0.95); decay 30-day half-life in promoter
- **Timestamp:** Promotion timestamp
- **Source attribution:** `source_trace_id` = `claude-memory-{name}`
- **Gap:** Promoted memories reach CanonicalMemoryStore but never InstanceRealityModel

### 4. Memory Watcher (partially governed — gap)
- **Owner:** `MemoryWatcher` (`substrate/memory/watcher.py`)
- **Storage:** Same as Claude memory sync
- **Write mechanism:** Same pipeline
- **Confidence:** Same type-based confidence
- **Timestamp:** File modification timestamp
- **Source attribution:** `source_trace_id` = `{agent}-memory-{name}`
- **Gap:** Same as Claude memory sync — missing reality bridge

### 5. Cockpit REST POST (ungoverned)
- **Owner:** `cockpit_reality_model_routes.py`
- **Storage:** `data/umh/reality_model/instance.jsonl`
- **Write mechanism:** Direct `InstanceRealityModel.record()` via HTTP POST
- **Confidence:** Caller-specified (no validation)
- **Timestamp:** Request time
- **Source attribution:** None — no source_system tracking
- **Gap:** Bypasses all mutation contracts; no source validation

### 6. Cockpit Self-Improvement (ungoverned)
- **Owner:** `cockpit_self_improvement_routes.py`
- **Storage:** `data/umh/reality_model/instance.jsonl`
- **Write mechanism:** Direct `InstanceRealityModel.record()` from self-improvement pipeline
- **Confidence:** Pipeline-generated
- **Timestamp:** Pipeline execution time
- **Source attribution:** Minimal — pipeline context only
- **Gap:** Same as cockpit REST — bypasses mutation contracts

### 7. IntentReceipts (audit-only — no gap)
- **Owner:** `IntentReceiptStore` (`substrate/operator/intent_receipt.py`)
- **Storage:** `data/umh/operator/intent_receipts.jsonl`
- **Write mechanism:** JSONL append-only
- **Confidence:** Classification confidence (0.0-1.0)
- **Timestamp:** `created_at` (time.time())
- **Source attribution:** `intent_id`, `route_type`
- **Gap:** None — receipts are audit artifacts, not reality observations (by design)

## Reality Model Architecture

### InstanceRealityModel (ephemeral, high-volume)
- Storage: `data/umh/reality_model/instance.jsonl`
- Decay: 14-day half-life
- Max: 5000 observations, auto-prune oldest
- Schema: `InstanceObservation` (Pydantic BaseModel)

### CanonicalRealityModel (sacred, governance-protected)
- Storage: `data/umh/reality_model/canonical.json`
- Decay: 180-day half-life
- Updates: Require `governance_approved=True`
- Schema: `CanonicalPattern` (Pydantic BaseModel)

### Convergence Point
All reality write paths terminate at `InstanceRealityModel.record(observation)`. Phase 19 creates a governed contract (`RealityMutation` → `CanonicalRealityWritePath.apply_mutation()`) to close gaps #2, #3, #4 without replacing the execution path (#1).
