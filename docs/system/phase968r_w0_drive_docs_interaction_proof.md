# Phase 96.8R — W0 Drive/Docs Interaction Proof

## Summary

Proves that the UMH substrate can route a Drive/Docs interaction through the
canonical control-plane path: Discord `!doc` command -> WorkPacket ->
ControlPlaneRouter -> adapter/runtime resolution -> simulated daemon proof ->
RouterResult -> Discord reply.

This is an **interaction proof only**. No document contents were read. No
screenshots were taken. No data was extracted. No memory was promoted.

## What was built

### New action type: `drive_open_safe_test_doc`

Wired through every layer:

| Layer | File | Change |
|-------|------|--------|
| Router contracts | `core/control_plane_router/router_contracts.py` | Added to `ALLOWED_ACTION_TYPES` |
| Capability map | `core/control_plane_router/control_plane_router_v1.py` | `ACTION_CAPABILITY_MAP` entry (GUI, requires_gui=True) |
| Adapter registry | `data/registries/local_worker_adapter_registry_v1.json` | Added capability to `windows_interactive_desktop_relay` |
| Router config | `config/control_plane_router_v1.json` | Added to `allowed_action_types` |
| Daemon config | `config/local_worker_runtime_daemon_v1.json` | Added to `supported_capabilities` |
| Discord adapter | `eos_ai/interfaces/discord_interface_adapter_v1.py` | `!doc` in `SUPPORTED_COMMANDS` and `COMMAND_ACTION_MAP` |
| Request builder | `core/environment_bridge/windows_desktop_request_builder.py` | `build_w0_drive_safe_test_doc_request()` |

### Interaction config

`config/w0_drive_docs_interaction_proof_v1.json` — defines safe URLs, forbidden
actions (11 blocked categories), proof requirements, and timeout.

### Proof script

`scripts/prove_w0_drive_docs_interaction.py` — 6-step dry-run proof:

1. WorkPacket creation from `!doc` command
2. Router dry-run decision (capability, adapter, runtime)
3. Forbidden actions verification (11 categories blocked)
4. Simulated daemon proof generation
5. RouterResult normalization + Discord formatting
6. Proof artifact writing

All 6 steps passed on VPS dry-run.

### Proof artifacts

Generated in `data/runtime/w0_interaction_proofs/`:

- `w0_drive_docs_work_packet_example.json` — WorkPacket with `no_secret_capture=true`, `no_mutation=true`
- `w0_drive_docs_runtime_proof_example.json` — Simulated RuntimeProof with evidence
- `w0_drive_docs_router_result_example.json` — Normalized RouterResult

All artifacts verified: no secrets, no extraction fields, no memory promotion fields.

## Safety enforcement

### Forbidden actions (11 categories)

| Category | Actions blocked |
|----------|----------------|
| Extraction | `read_document_contents`, `copy_text`, `download_file`, `upload_file` |
| Capture | `take_screenshot`, `capture_ocr` |
| Mutation | `mutate_drive`, `mutate_docs` |
| Secrets | `extract_cookies`, `extract_tokens` |
| Memory | `promote_memory` |

### Payload constraints

- `no_secret_capture: true`
- `no_mutation: true`
- `launch_method: direct_executable`
- `blocked_launch_methods: [explorer_url, default_browser]`
- No `document_content`, `extracted_text`, `file_contents`, `screenshot_path` fields
- No `promote_to_memory`, `memory_target`, `ingest` fields

## Test coverage

27 tests in `tests/test_w0_drive_docs_interaction_proof.py`:

| Suite | Tests | Coverage |
|-------|-------|----------|
| TestDocCommandRegistered | 4 | Command/action wiring |
| TestSafeDocWorkPacket | 7 | Packet construction, URL, safety flags |
| TestArbitraryUrlRejected | 2 | Unknown command rejection |
| TestForbiddenActionsBlocked | 3 | Payload forbidden action scan |
| TestRouterResolvesDocAction | 2 | Router dry-run resolution |
| TestInteractionConfig | 5 | Config schema validation |
| TestProofArtifactSchemas | 4 | Artifact existence and no-secrets scan |

Full substrate suite: **127 tests, 0 failures, 0 regressions**.

## Routing chain

```
Discord !doc
  -> COMMAND_ACTION_MAP["!doc"] = "drive_open_safe_test_doc"
  -> build_w0_drive_safe_test_doc_request(safe_doc_url)
  -> WorkPacket(action_type="drive_open_safe_test_doc")
  -> ControlPlaneRouterV1.route_dry_run()
     -> validate_packet(): action in ALLOWED_ACTION_TYPES
     -> resolve_capability(): WINDOWS_GUI_EXECUTION (requires_gui=True)
     -> resolve_adapter(): windows_interactive_desktop_relay
     -> resolve_runtime(): local_worker_runtime_daemon
  -> RouterResult(status=ROUTED)
```

## What this does NOT prove

- Document was NOT opened (VPS dry-run only)
- Chrome was NOT launched
- No founder visual confirmation obtained
- No content was accessed or extracted
- No live daemon was involved

## Live execution path (next phase)

1. Start daemon: `python3 eos_ai/substrate/local_worker_runtime_daemon.py --config config/local_worker_runtime_daemon_v1.json`
2. Start relay: `.\scripts\windows_interactive_desktop_relay.ps1`
3. Start Discord: `python3 eos_ai/interfaces/discord_interface_adapter_v1.py`
4. Send `!doc` in Discord
5. Confirm test document visible in Chrome
6. Verify RuntimeProof returned to Discord

## Phase gate

- [x] Action type wired through all layers
- [x] Forbidden actions enforced (11 categories)
- [x] No extraction, no mutation, no secrets in payload
- [x] Proof script runs clean (6/6 steps)
- [x] Proof artifacts generated and validated
- [x] 27 focused tests pass
- [x] 127 total substrate tests pass (0 regressions)
- [ ] Live execution (requires local WSL + founder confirmation)
