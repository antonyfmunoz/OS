# Phase 96.8T — W0 Document Ingestion Candidate Proof

## Summary

Proves that the UMH substrate can convert a bounded safe document extraction
result into normalized ingestion candidate and memory candidate artifacts,
then stop at the governance boundary before any promotion occurs.

This is an **ingestion candidate proof only**. No memory was promoted. No
canonical writes occurred. No world model was updated. No embeddings were
generated. No content was interpreted or summarized. The candidate artifacts
describe what *would* happen if governance approved promotion — without
actually doing it.

## Extraction vs ingestion candidate vs memory promotion

| Stage | What happens | Side effects | This phase |
|-------|-------------|--------------|------------|
| Extraction (96.8S) | Read content from safe doc | Text preview returned | Upstream |
| Ingestion candidate (96.8T) | Normalize extraction into structured candidate | Candidate artifacts written | **This** |
| Memory promotion (future) | Write candidate to canonical knowledge | Memory table updated | Next gate |

The ingestion candidate is a *proposal*, not an action. It contains:
- The normalized text preview (bounded)
- A SHA-256 content hash (deterministic, verifiable)
- Source metadata (title, URL, extraction reference)
- Confidence scores
- A `promotion_status: "candidate_only"` field that blocks promotion
- A `governance_required: true` field that requires founder approval

The memory candidate adds:
- `allowed_next_actions` (review, approve, reject, re-extract)
- `blocked_next_actions` (promote, canonical write, world model, embeddings, interpret, summarize)
- `requires_review: true`

## What was built

### New action type: `doc_ingestion_candidate_safe_test_doc`

Wired through every layer:

| Layer | File | Change |
|-------|------|--------|
| Router contracts | `core/control_plane_router/router_contracts.py` | Added to `ALLOWED_ACTION_TYPES`, new `INGESTION_CANDIDACY` capability type |
| Capability map | `core/control_plane_router/control_plane_router_v1.py` | `ACTION_CAPABILITY_MAP` entry (INGESTION_CANDIDACY, requires_gui=False) |
| Adapter registry | `data/registries/local_worker_adapter_registry_v1.json` | Added capability to `windows_interactive_desktop_relay` |
| Router config | `config/control_plane_router_v1.json` | Added to `allowed_action_types` |
| Daemon config | `config/local_worker_runtime_daemon_v1.json` | Added to `supported_capabilities` |
| Discord adapter | `eos_ai/interfaces/discord_interface_adapter_v1.py` | `!ingest-candidate` in `SUPPORTED_COMMANDS` and `COMMAND_ACTION_MAP` |
| Request builder | `core/environment_bridge/windows_desktop_request_builder.py` | `build_w0_doc_ingestion_candidate_request()` |

### New capability type: `INGESTION_CANDIDACY`

Ingestion candidacy does not require GUI. It normalizes extraction results
into structured candidates. The capability distinction from `DOCUMENT_EXTRACTION`
is intentional: extraction reads content; candidacy structures it for review.
`requires_gui: false` because candidate creation is a data normalization step,
not a desktop operation.

### Ingestion config

`config/w0_doc_ingestion_candidate_proof_v1.json` — defines safe doc target,
15 forbidden actions, governance gate (founder approval required), proof
requirements, and timeout.

### Ingestion candidate schema (15 fields)

```
candidate_id, source_type, source_title, source_id_or_url,
extraction_reference_id, normalized_text_preview, normalized_character_count,
content_hash, source_confidence, extraction_confidence, candidate_status,
promotion_status, governance_required, forbidden_actions_confirmed, timestamp
```

### Memory candidate schema (12 fields)

```
memory_candidate_id, candidate_id, memory_type, scope, source, confidence,
content_preview, promotion_status, requires_review, allowed_next_actions,
blocked_next_actions, timestamp
```

### Proof script

`scripts/prove_w0_doc_ingestion_candidate.py` — 9-step dry-run proof:

1. WorkPacket creation from `!ingest-candidate`
2. Router dry-run decision (INGESTION_CANDIDACY capability)
3. Forbidden actions verification (15 categories)
4. Ingestion candidate schema validation (15 fields)
5. Memory candidate schema validation (12 fields)
6. Governance boundary enforcement
7. Simulated daemon proof
8. RouterResult normalization + Discord formatting
9. Proof artifact writing

All 9 steps passed on VPS dry-run.

### Proof artifacts

Generated in `data/runtime/w0_ingestion_candidates/`:

- `w0_doc_ingestion_work_packet_example.json`
- `w0_doc_ingestion_runtime_proof_example.json`
- `w0_doc_ingestion_candidate_example.json`
- `w0_doc_memory_candidate_example.json`
- `w0_doc_ingestion_router_result_example.json`

## Data boundary

The governance boundary is enforced at two levels:

1. **Ingestion candidate**: `promotion_status: "candidate_only"`,
   `governance_required: true`
2. **Memory candidate**: `promotion_status: "candidate_only"`,
   `requires_review: true`, `blocked_next_actions` includes all promotion verbs

No code path exists in this phase to change `promotion_status` from
`candidate_only` to any promoted state. The schema itself encodes the
governance requirement — a consumer that reads the candidate knows it
cannot act on it without governance approval.

## Why candidate creation is safe

1. **No writes**: Candidates are written to the proof artifacts directory,
   not to any canonical memory store, database, or knowledge base
2. **No interpretation**: Raw text is normalized, not analyzed or summarized
3. **No embeddings**: No vector representations generated
4. **No world model**: No ambient state updated
5. **Content hash**: SHA-256 hash provides integrity verification without
   requiring the full content to be stored or transmitted

## Policy constraints

### Forbidden actions (15 categories)

| Category | Actions blocked |
|----------|----------------|
| Promotion | `promote_memory`, `canonical_write`, `world_model_update` |
| Embeddings | `generate_embeddings` |
| Interpretation | `interpret_content`, `summarize_content` |
| Search | `drive_wide_ingestion`, `arbitrary_url_open`, `recursive_crawl` |
| Capture | `take_screenshot`, `capture_ocr` |
| Mutation | `mutate_drive`, `mutate_docs` |
| Secrets | `extract_cookies`, `extract_tokens` |

## Test coverage

55 tests in `tests/test_w0_doc_ingestion_candidate_proof.py`:

| Suite | Tests | Coverage |
|-------|-------|----------|
| TestIngestCandidateCommandRegistered | 4 | Command wiring, INGESTION_CANDIDACY type |
| TestIngestionCandidateWorkPacket | 7 | Packet construction, safety, governance notes |
| TestArbitraryTargetRejected | 3 | Unknown commands, action isolation |
| TestForbiddenActionsBlocked | 5 | No canonical/embedding/interpretation/world fields |
| TestRouterResolvesIngestionCandidateAction | 2 | Router dry-run |
| TestIngestionConfig | 7 | Config schema, governance gate |
| TestIngestionCandidateSchema | 9 | 15 fields, hash determinism, promotion blocked |
| TestMemoryCandidateSchema | 14 | 12 fields, all blocked/allowed actions |
| TestProofArtifactSchemas | 4 | Artifact existence, no secrets, evidence flags |

Full substrate suite: **227 tests, 0 failures, 0 regressions**.

## What governance must approve before promotion

Before any memory candidate can be promoted to canonical knowledge:

1. **Founder explicit approval** — via command (not automated)
2. **Source verification** — confirm the document is the intended safe test doc
3. **Content review** — preview matches expected test content
4. **Hash verification** — SHA-256 matches extraction content
5. **Scope confirmation** — knowledge target is appropriate
6. **Promotion path validation** — destination table/store is correct

## What remains unproven

- Live extraction feeding real content into candidate creation
- Governance approval workflow execution
- Actual memory write after governance approval
- Content hash verification against live extraction
- Rejection workflow (candidate denied)
- Re-extraction workflow (candidate sent back)

## Next gate

**W0_MEMORY_PROMOTION_GOVERNANCE_PROOF** — prove that a governed approval
workflow can transition a candidate from `candidate_only` to `approved`
and execute a bounded canonical write. Still single safe test doc only.
Still founder-gated.

## Phase gate

- [x] Action type wired through all 7 layers
- [x] New INGESTION_CANDIDACY capability type
- [x] Forbidden actions enforced (15 categories)
- [x] Ingestion candidate schema validated (15 fields)
- [x] Memory candidate schema validated (12 fields)
- [x] Content hash generated (SHA-256, deterministic)
- [x] Governance boundary enforced (promotion_status=candidate_only)
- [x] No canonical memory writes
- [x] No world model updates
- [x] No embeddings generated
- [x] Proof script runs clean (9/9 steps)
- [x] Proof artifacts generated and validated (5 files)
- [x] 55 focused tests pass
- [x] 227 total substrate tests pass (0 regressions)
- [ ] Live candidate creation (requires live extraction upstream)
