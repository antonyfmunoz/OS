# Discovery — Orchestrator Unification (Phase 0)

> Date: 2026-05-12
> Status: STOP CONDITION TRIGGERED — see Section 5

---

## 1. Callers of FullLiveIngestionSpine

| File | Lines | Call Shape | Context |
|------|-------|-----------|---------|
| `tests/test_full_live_ingestion_completion_v1.py` | L67-68, L140-144 | `FullLiveIngestionSpine(config, ledger, proof_dir)` → `.execute_full_ingestion(content)` | Tests — 25 test classes, 58 test methods |
| `core/runtime/full_live_ingestion_spine_v1.py` | L226 | Class definition | Source module |

**No production callers. No cron callers. No service callers.**
The spine is only consumed by its own test suite. No runtime service
imports or calls it. The Discord spine integration routes through
`discord_spine_integration_v1.py` → `build_spine_infrastructure()`,
which builds its own infrastructure and calls `execute_spine_command()`.

---

## 2. Constructor Signature

```python
def __init__(
    self,
    config: dict[str, Any],
    ledger: TransformationStateLedger,
    proof_dir: Path | None = None,
) -> None:
```

Dependencies:
- `config` — GWS-specific keys: `google_account_identity`, `adapter_instance_id`,
  `safe_doc_url_or_id`, `safe_doc_title`, `max_extract_chars`, `preview_char_limit`
- `ledger` — `TransformationStateLedger` instance
- `proof_dir` — optional dir for proof JSON files

Internally constructs:
- `self._identity` — `IdentityScopedMetadata` (GWS-specific)
- `self._drive_adapter` — `GoogleDriveAdapterV1(config)`
- `self._docs_adapter` — `GoogleDocsAdapterV1(config)`
- `self._forbidden` — `INGESTION_FORBIDDEN_ACTIONS`

---

## 3. Public Methods

| Method | Signature | Return |
|--------|-----------|--------|
| `identity` | `@property` | `IdentityScopedMetadata` |
| `forbidden_actions` | `@property` | `list[str]` |
| `validate_safe_doc_target()` | `() -> list[str]` | error list |
| `validate_url_is_safe(url: str)` | `(str) -> list[str]` | error list |
| `execute_full_ingestion(api_raw_content, trace_id, runtime_id)` | `(str, str, str) -> IngestionSpineResult` | full result |

---

## 4. Internal Pipeline Order

1. Validate safe doc targeting (deny-if-misconfigured)
2. Bound extraction content (truncate to `max_extract_chars`)
3. Drive open via `GoogleDriveAdapterV1.open_safe_drive()`
4. Extract via `GoogleDocsAdapterV1.extract()`
5. Normalize via `GoogleDocsAdapterV1.normalize()`
6. Primitive decomposition (hash-based, no LLM)
7. `IngestionCandidate` construction
8. `MemoryCandidate` construction
9. Replay validation (reconstruct trace, verify determinism)
10. Build `IngestionProof`, persist to file
11. Return `IngestionSpineResult`

Each step (2-8) records an `IngestionLedgerState` + `StateLedgerRecord`
into the `TransformationStateLedger`.

---

## 5. GWS-SPECIFIC BEHAVIOR COUPLED TO PIPELINE SEQUENCING

### STOP CONDITION TRIGGERED

The following GWS-specific behaviors are **inseparable from the pipeline
sequencing** inside `FullLiveIngestionSpine`. They cannot be cleanly moved
into a `GWSSource` adapter:

#### A. TransformationStateLedger integration (lines 316-374)
Every pipeline stage records a `StateLedgerRecord` with:
- Stage name (`drive_docs_opened`, `document_extracted`, etc.)
- Input/output hashes chained parent→child
- `policy_envelope` with phase, governance, identity
- `transformer_name="full_live_ingestion_spine_v1"`
- Forbidden/allowed next-action lists per stage

The `GenericIngestionOrchestrator` has NO ledger integration. It uses a
completely different tracking mechanism (duration_ms per stage, Signal +
InterpretationResult + DecompositionResult chain). Delegating to the
orchestrator would lose all ledger records.

#### B. Different output dataclasses
- Spine returns `IngestionSpineResult` (drive_open_proof, extraction_result,
  normalized_extraction, primitive_decomposition, ingestion_candidate,
  memory_candidate, replay_result, ledger_states, ingestion_proof)
- Orchestrator returns `IngestionResult` (signal, interpretation,
  decomposition, world_update, memory_write, promotion_receipt, query_proof)

These are completely different field sets. **Not mappable without
fabricating fake data** for the fields the orchestrator doesn't produce.

#### C. Different pipeline stages
- Spine: validate → drive_open → extract → normalize → decompose →
  ingestion_candidate → memory_candidate → replay → proof
- Orchestrator: perceive → interpret → decompose → map → persist → query_back

These are not the same stages. The spine uses GWS adapters (Drive, Docs)
directly. The orchestrator uses Source.read() + its own interpret/map/persist.

#### D. IngestionCandidate / MemoryCandidate (lines 447-488)
The spine constructs these from pipeline-specific contracts
(`IngestionCandidate`, `MemoryCandidate` from
`live_drive_docs_ingestion_pipeline_v1`). The orchestrator doesn't use
these contracts at all — it writes directly to `memories.jsonl`.

#### E. Replay validation (lines 490-533)
The spine reconstructs the full trace from `TransformationStateLedger`,
builds a `ReplayQueryResult`, and verifies determinism. The orchestrator
has no replay mechanism.

#### F. GoogleDriveAdapterV1 / GoogleDocsAdapterV1 (lines 389-427)
The spine calls `open_safe_drive()`, `extract()`, `normalize()` directly
on adapter instances. These are not source reads — they're multi-step
extraction with GWS-specific normalization logic. A `GWSSource.read()`
would need to replicate all three steps internally, returning a single
`RawContent` — but the spine exposes intermediate results
(drive_open_proof, extraction_result, normalized_extraction) as separate
fields in its output.

### CONCLUSION

The `FullLiveIngestionSpine` is not "the orchestrator pipeline with a GWS
source plugged in." It is a fundamentally different pipeline with:
- Different stages
- Different output shapes
- Different tracking (ledger vs. duration-based)
- Different persistence (proof files vs. memories.jsonl)
- Different contracts (IngestionCandidate/MemoryCandidate vs. MemoryWrite)

Forcing it into a wrapper around `GenericIngestionOrchestrator` would
require either:
1. **Fabricating fake data** — filling `IngestionSpineResult` fields with
   data the orchestrator doesn't produce (violates equivalence)
2. **Breaking the public API** — changing what callers see (violates
   the safety gate)
3. **Running both pipelines** — orchestrator for real work, spine logic
   for ledger/replay/proof artifacts (doubles execution cost, creates
   divergence risk)

None of these are acceptable.

---

## 6. Recommended Path Forward

Instead of wrapping the spine around the orchestrator, the correct
unification is:

**Option A — Deprecation path**: Keep both as independent implementations.
Mark `FullLiveIngestionSpine` as deprecated. New GWS ingestion should
use `GenericIngestionOrchestrator` + `GWSSource` directly. The spine
stays for its existing callers (tests only) until they're migrated.

**Option B — Build GWSSource independently**: Create `GWSSource` that
wraps `gws_scanner` as a Source implementation. Use it with
`GenericIngestionOrchestrator` directly. The spine remains untouched.
This gives GWS ingestion via the canonical path without breaking the
spine.

Option B delivers the stated goal (GWS docs through the canonical
pipeline) without the risk of a wrapper refactor that would require
fabricating data or breaking the public API.

---

## 7. GWSSource — Still Viable as Independent Source

`GWSSource` wrapping `gws_scanner.py` is straightforward and valuable:
- `read()` → calls `scanner.read_doc(doc_id)` → returns `RawContent`
- `metadata()` → maps GWS doc metadata → standard dict
- `exists()` → calls `scanner.list_all_docs()` or uses cached metadata

This can be used with `GenericIngestionOrchestrator` directly for new
GWS ingestion, without touching the spine at all.
