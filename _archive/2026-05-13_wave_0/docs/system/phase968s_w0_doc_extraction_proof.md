# Phase 96.8S — W0 Safe Document Extraction Proof

## Summary

Proves that the UMH substrate can route a bounded document extraction
through the canonical control-plane path: Discord `!extract` command ->
WorkPacket -> ControlPlaneRouter -> adapter/runtime resolution ->
simulated extraction + schema validation -> RuntimeProof -> RouterResult
-> Discord reply.

This is an **extraction proof only**. No content was ingested. No content
was interpreted or summarized. No memory was promoted. Extraction is bounded
to one configured safe test document with a character-limited preview.

## Extraction proof vs ingestion

| Concern | Extraction (this phase) | Ingestion (future) |
|---------|------------------------|-------------------|
| Scope | One configured safe doc | Configured doc set |
| Output | Raw text preview + schema | Structured knowledge records |
| Interpretation | None | LLM analysis of content |
| Memory | No promotion | Writes to knowledge base |
| Confidence | Schema-validated | Interpretation confidence |
| Mutation | None | None |

Extraction proves the substrate can read content back from a document.
Ingestion would process that content into the knowledge system.
This phase proves extraction without crossing into ingestion territory.

## What was built

### New action type: `doc_extract_safe_test_doc`

Wired through every layer:

| Layer | File | Change |
|-------|------|--------|
| Router contracts | `core/control_plane_router/router_contracts.py` | Added to `ALLOWED_ACTION_TYPES`, new `DOCUMENT_EXTRACTION` capability type |
| Capability map | `core/control_plane_router/control_plane_router_v1.py` | `ACTION_CAPABILITY_MAP` entry (DOCUMENT_EXTRACTION, requires_gui=True) |
| Adapter registry | `data/registries/local_worker_adapter_registry_v1.json` | Added capability to `windows_interactive_desktop_relay` |
| Router config | `config/control_plane_router_v1.json` | Added to `allowed_action_types` |
| Daemon config | `config/local_worker_runtime_daemon_v1.json` | Added to `supported_capabilities` |
| Discord adapter | `eos_ai/interfaces/discord_interface_adapter_v1.py` | `!extract` in `SUPPORTED_COMMANDS` and `COMMAND_ACTION_MAP` |
| Request builder | `core/environment_bridge/windows_desktop_request_builder.py` | `build_w0_doc_extract_safe_test_doc_request()` |

### New capability type: `DOCUMENT_EXTRACTION`

Extraction requires a fundamentally different trust boundary than
`WINDOWS_GUI_EXECUTION`. Opening a URL is fire-and-forget — the relay
launches Chrome and reports a window title. Extraction reads content back
into the system. A new `CapabilityType` signals this distinction to every
layer in the routing chain.

### Extraction config

`config/w0_doc_extraction_proof_v1.json` — defines safe doc URL/title/ID,
extraction method, preview max chars (500), 14 forbidden actions, proof
requirements, and timeout.

### Extraction result schema

10 required fields:

```
request_id, action_type, target_doc_id_or_title, extraction_method,
extracted_text_preview, extracted_character_count, extraction_confidence,
proof_status, forbidden_actions_confirmed, timestamp
```

Preview bounded to `extraction_preview_max_chars` from config (500).
Confidence restricted to `high`, `medium`, `low`.

### Proof script

`scripts/prove_w0_doc_extraction.py` — 7-step dry-run proof:

1. WorkPacket creation from `!extract` command
2. Router dry-run decision (capability, adapter, runtime)
3. Forbidden actions verification (14 categories blocked)
4. Extraction result schema validation (10 fields, preview bounded)
5. Simulated daemon extraction proof
6. RouterResult normalization + Discord formatting
7. Proof artifact writing

All 7 steps passed on VPS dry-run.

### Proof artifacts

Generated in `data/runtime/w0_extraction_proofs/`:

- `w0_doc_extraction_work_packet_example.json`
- `w0_doc_extraction_runtime_proof_example.json`
- `w0_doc_extraction_result_example.json`
- `w0_doc_extraction_router_result_example.json`

All artifacts verified: no secrets, no ingestion fields, no memory promotion.

## Environment chain

```
Discord !extract
  -> COMMAND_ACTION_MAP["!extract"] = "doc_extract_safe_test_doc"
  -> build_w0_doc_extract_safe_test_doc_request(safe_doc_url, safe_doc_title)
  -> WorkPacket(action_type="doc_extract_safe_test_doc")
  -> ControlPlaneRouterV1.route_dry_run()
     -> validate_packet(): action in ALLOWED_ACTION_TYPES
     -> resolve_capability(): DOCUMENT_EXTRACTION (requires_gui=True)
     -> resolve_adapter(): windows_interactive_desktop_relay
     -> resolve_runtime(): local_worker_runtime_daemon
  -> RouterResult(status=ROUTED)
  -> [live: daemon extracts text from configured doc via API/relay]
  -> ExtractionResult(preview bounded, schema validated)
  -> RuntimeProof(extraction_completed=True)
  -> RouterResult(status=COMPLETED)
```

## Extraction method

Configured as `google_docs_api_export_text`. In live execution, the relay
would use the Google Docs API to export the document as plain text, bounded
by the configured preview max. No GUI scraping, no screenshots, no OCR.

## Policy constraints

### Forbidden actions (14 categories)

| Category | Actions blocked |
|----------|----------------|
| Search | `drive_wide_search`, `arbitrary_url_open` |
| Capture | `take_screenshot`, `capture_ocr` |
| Transfer | `download_file`, `upload_file` |
| Mutation | `mutate_drive`, `mutate_docs` |
| Secrets | `extract_cookies`, `extract_tokens` |
| Memory | `promote_memory`, `ingest_to_memory` |
| Interpretation | `interpret_content`, `summarize_content` |

### Payload constraints

- `no_secret_capture: true`
- `no_mutation: true`
- `launch_method: direct_executable`
- `blocked_launch_methods: [explorer_url, default_browser, ...]`
- No ingestion fields (`ingest_target`, `memory_target`, `knowledge_base_target`)
- No interpretation fields (`interpret`, `summarize`, `llm_analysis`)
- No screenshot fields (`screenshot_path`, `ocr_result`, `capture_image`)

## Test coverage

45 tests in `tests/test_w0_doc_extraction_proof.py`:

| Suite | Tests | Coverage |
|-------|-------|----------|
| TestExtractCommandRegistered | 4 | Command/action wiring, capability type |
| TestExtractionWorkPacket | 8 | Packet construction, URL, safety flags, notes |
| TestArbitraryTargetRejected | 3 | Unknown commands, action isolation |
| TestForbiddenActionsBlocked | 5 | Payload scan, no ingestion/interpretation/memory/screenshot |
| TestRouterResolvesExtractAction | 2 | Router dry-run, DOCUMENT_EXTRACTION capability |
| TestExtractionConfig | 10 | Config schema, all forbidden categories |
| TestExtractionResultSchema | 8 | Schema fields, preview bounded, confidence valid |
| TestProofArtifactSchemas | 5 | Artifact existence, no secrets |

Full substrate suite: **172 tests, 0 failures, 0 regressions**.

## What this does NOT prove

- Document was NOT extracted (VPS dry-run, simulated text)
- Chrome was NOT launched
- Google Docs API was NOT called
- No founder visual confirmation obtained
- No live daemon involved
- Extraction text is placeholder/simulated

## What remains unproven

- Live API-based extraction from the safe test document
- Extraction preview truncation with real document content
- Google Docs API authentication and export flow
- Relay-to-daemon extraction result forwarding
- End-to-end Discord !extract with real extraction result

## Next gate

**W0_DOC_INGESTION_CANDIDATE_PROOF** — prove that extracted content can
be structured into an ingestion candidate record without actually ingesting.
Ingestion candidates would include: source document reference, extracted
text, metadata, proposed knowledge base target, and ingestion policy check.
Still no LLM interpretation, still no memory promotion.

## Phase gate

- [x] Action type wired through all 7 layers
- [x] New DOCUMENT_EXTRACTION capability type
- [x] Forbidden actions enforced (14 categories)
- [x] No ingestion, no interpretation, no memory promotion in payload
- [x] Extraction result schema validated (10 fields)
- [x] Preview length bounded (500 chars max)
- [x] Proof script runs clean (7/7 steps)
- [x] Proof artifacts generated and validated (4 files)
- [x] 45 focused tests pass
- [x] 172 total substrate tests pass (0 regressions)
- [ ] Live extraction (requires local WSL + Google Docs API + founder confirmation)
