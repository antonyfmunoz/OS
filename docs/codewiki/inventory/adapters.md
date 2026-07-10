---
type: codewiki-inventory
dir: adapters
source_sha: 70deadbac8667755a38ac49595afd09afc209c2f
---

# `adapters/` — File Inventory

**Files:** 101 regular + 0 symlinks · **Bytes:** 780,940

[Narrative page](../dirs/adapters.md)


## adapters/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/README.md` | 30 | adapters/ |
| `adapters/__init__.py` | 0 | package marker (empty) |
| `adapters/protocol.py` | 19 | — |
| `adapters/socket_registration.py` | 213 | Socket registration — wires concrete adapters into substrate ports. |

## adapters/adapter_engine/ (17 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/adapter_engine/__init__.py` | 29 | Adapter engine — manifest, maturity, lifecycle, and registry for UMH adapters. |
| `adapters/adapter_engine/adapter_lifecycle_manager_v1.py` | 246 | Adapter Lifecycle Manager v1 for the canonical runtime spine. |
| `adapters/adapter_engine/adapter_manifest.py` | 96 | Unified adapter manifest for the UMH substrate layer. |
| `adapters/adapter_engine/adapter_maturity.py` | 201 | Generalized adapter maturity evidence model. |
| `adapters/adapter_engine/adapter_registry_contracts.py` | 156 | Adapter registry contracts for the UMH substrate layer. |
| `adapters/adapter_engine/capability_catalog.py` | 65 | Per-adapter capability catalog for the UMH substrate layer. |
| `adapters/adapter_engine/capability_discovery.py` | 375 | Capability discovery orchestrator for the UMH substrate layer. |
| `adapters/adapter_engine/cu_api_parity_v1.py` | 259 | CU / API Parity Validator v1 for the UMH substrate layer. |
| `adapters/adapter_engine/google_docs_adapter_v1.py` | 396 | Google Docs Adapter v1 for the UMH substrate layer. |
| `adapters/adapter_engine/google_drive_adapter_v1.py` | 287 | Google Drive Adapter v1 for the UMH substrate layer. |
| `adapters/adapter_engine/gws_scanner_bridge_v1.py` | 175 | GWS Scanner Bridge v1 — translates existing scanner outputs into substrate ingestion contracts. |
| `adapters/adapter_engine/live_drive_docs_ingestion_pipeline_v1.py` | 735 | Live Drive/Docs Ingestion Pipeline v1 for the UMH substrate layer. |
| `adapters/adapter_engine/modality.py` | 21 | Communication modality types for UMH adapters. |
| `adapters/adapter_engine/participant.py` | 20 | Participant type classification for UMH adapters. |
| `adapters/adapter_engine/production_manifests.py` | 429 | Production adapter manifests for all live adapter families. |
| `adapters/adapter_engine/substrate_candidate_gen_v1.py` | 217 | Substrate Candidate Generation v1 — generates ingestion candidates from decomposition. |
| `adapters/adapter_engine/substrate_decomposer_v1.py` | 284 | Substrate Decomposer v1 — deterministic primitive decomposition from normalized documents. |

## adapters/broadcast/ (10 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/broadcast/__init__.py` | 0 | package marker (empty) |
| `adapters/broadcast/engine.py` | 324 | Broadcast engine — owns FFmpeg subprocess lifecycle, config->args, health. |
| `adapters/broadcast/ffmpeg_args.py` | 252 | Pure deterministic config -> FFmpeg CLI argument list. |
| `adapters/broadcast/filtergraph.py` | 216 | Filtergraph builder — scene config -> FFmpeg -filter_complex args. |
| `adapters/broadcast/integration/__init__.py` | 0 | package marker (empty) |
| `adapters/broadcast/integration/handlers.py` | 226 | Broadcast capability handler — implements CapabilityHandler Protocol. |
| `adapters/broadcast/integration/manifest.py` | 62 | Broadcast integration manifest — declares capabilities for start, stop, status. |
| `adapters/broadcast/process_lifecycle.py` | 207 | Subsystem-agnostic subprocess lifecycle manager. |
| `adapters/broadcast/scene_model.py` | 125 | Scene + SourceEntry models for multi-source compositing. |
| `adapters/broadcast/zmq_client.py` | 137 | ZMQ command client for live FFmpeg filter parameter control. |

## adapters/browser/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/browser/__init__.py` | 10 | Browser adapter — re-exports from substrate execution layer. |

## adapters/browser_auth/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/browser_auth/__init__.py` | 0 | package marker (empty) |
| `adapters/browser_auth/clerk_auth.py` | 253 | Clerk browser auth adapter — single login flow for all UMH browser automation. |
| `adapters/browser_auth/sso_chain.py` | 115 | SSO chain auth adapter — follows OAuth redirects through GitHub/Google. |

## adapters/browser_exports/ (8 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/browser_exports/__init__.py` | 27 | Browser export adapters — autonomous data export from web services. |
| `adapters/browser_exports/chatgpt_export.py` | 194 | ChatGPT data export trigger — deterministic Playwright script. |
| `adapters/browser_exports/claude_export.py` | 191 | Claude data export trigger — deterministic Playwright script. |
| `adapters/browser_exports/contract.py` | 29 | Browser export contract — data classes for export requests and results. |
| `adapters/browser_exports/gmail_export_poller.py` | 121 | Gmail export email poller — finds export download links in inbox. |
| `adapters/browser_exports/instagram_export.py` | 208 | Instagram saved posts export — scrapes saved collection via Playwright. |
| `adapters/browser_exports/instagram_export_parser.py` | 537 | Instagram curation analyst — classifies saved posts and scores harness candidates. |
| `adapters/browser_exports/profile_manager.py` | 183 | ProfileManager — persistent browser context for authenticated exports. |

## adapters/calendar/ (3 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/calendar/__init__.py` | 0 | package marker (empty) |
| `adapters/calendar/meetings.py` | 836 | Meetings — central module for all meeting lifecycle management. |
| `adapters/calendar/travel_manager.py` | 348 | Travel Manager — full trip logistics management. |

## adapters/data_source_adapters/ (8 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/data_source_adapters/__init__.py` | 0 | package marker (empty) |
| `adapters/data_source_adapters/conversation_source.py` | 107 | ConversationSource — wraps parsed conversation data as an ingestion Source. |
| `adapters/data_source_adapters/github_source.py` | 307 | GitHubRepoSource — reads a single file from a cloned GitHub repo as an ingestion source. |
| `adapters/data_source_adapters/gws_source.py` | 88 | GWSSource — wraps GWSDocumentScanner as an ingestion Source. |
| `adapters/data_source_adapters/local_file_source.py` | 58 | LocalFileSource — reads a single local file as an ingestion source. |
| `adapters/data_source_adapters/parsers/__init__.py` | 6 | Conversation export parsers for UMH ingestion pipeline. |
| `adapters/data_source_adapters/parsers/chatgpt_parser.py` | 256 | ChatGPT conversation export parser. |
| `adapters/data_source_adapters/parsers/claude_parser.py` | 175 | Claude conversation export parser. |

## adapters/github/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/github/__init__.py` | 0 | package marker (empty) |
| `adapters/github/github_operations.py` | 230 | GitHub Operations — governed write operations for GitHub via gh CLI. |

## adapters/google_workspace/ (7 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/google_workspace/__init__.py` | 0 | package marker (empty) |
| `adapters/google_workspace/doc_creator.py` | 366 | Document Creator — generates briefing docs, board updates, |
| `adapters/google_workspace/document_filer.py` | 137 | Document Filing System — intelligently files documents |
| `adapters/google_workspace/email_gps.py` | 1,429 | EmailGPS — 7-folder email management system for DEX. |
| `adapters/google_workspace/gws_connector.py` | 1,116 | GWSConnector — Google Workspace integration via gws CLI. |
| `adapters/google_workspace/gws_scanner.py` | 703 | GWSDocumentScanner — reads Google Docs the founder owns, |
| `adapters/google_workspace/tasks_adapter.py` | 88 | Google Tasks adapter — thin wrapper over GWSConnector task methods. |

## adapters/models/ (11 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/models/__init__.py` | 0 | package marker (empty) |
| `adapters/models/agent_runtime.py` | 580 | Agent runtime for OS agents. |
| `adapters/models/cc_sdk.py` | 513 | cc_sdk — Claude Code Agent SDK wrapper for UMH. |
| `adapters/models/codex_cli.py` | 263 | codex_cli — Codex CLI adapter for EOS. |
| `adapters/models/hermes_cli.py` | 1,025 | hermes_cli — Hermes Agent runtime adapter for UMH. |
| `adapters/models/llm_adapter.py` | 91 | LLMAdapter — wraps model_router.call_with_fallback() as a substrate Adapter. |
| `adapters/models/model_router.py` | 1,618 | ModelRouter — standalone multi-model router for EOS. |
| `adapters/models/opencode_cli.py` | 183 | opencode_cli — OpenCode CLI adapter for EOS. |
| `adapters/models/routing/__init__.py` | 16 | Model routing — symbolic capability classes and routing config. |
| `adapters/models/routing/capabilities.py` | 123 | Symbolic capability classes for model routing. |
| `adapters/models/routing/config.py` | 128 | Routing config — maps capability classes to runtime/model_router kwargs. |

## adapters/notebooklm/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/notebooklm/__init__.py` | 0 | package marker (empty) |
| `adapters/notebooklm/notebooklm_sync.py` | 308 | NotebookLMSync — bidirectional sync between Neon and NotebookLM. |

## adapters/notion/ (13 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/notion/__init__.py` | 0 | package marker (empty) |
| `adapters/notion/integration/DESIGN.md` | 375 | Notion Integration — Design Report |
| `adapters/notion/integration/__init__.py` | 1 | Notion integration — manifest, handler, transforms, signals, outcomes. |
| `adapters/notion/integration/auth.py` | 64 | Notion auth — credential loading from environment. |
| `adapters/notion/integration/correlation.py` | 40 | Thread-safe in-memory correlation map for outcome writeback targeting. |
| `adapters/notion/integration/handlers.py` | 214 | Notion capability handler — implements CapabilityHandler Protocol. |
| `adapters/notion/integration/manifest.py` | 124 | Notion integration manifest — declares sockets, signals, capabilities, signal sources. |
| `adapters/notion/integration/outcomes.py` | 139 | Notion outcome receiver — writes pipeline outcomes back to Notion pages. |
| `adapters/notion/integration/poller.py` | 217 | Notion poller — background thread that polls databases for changes. |
| `adapters/notion/integration/signals.py` | 103 | Notion signal emitter — builds SignalEnvelopes from polled Notion pages. |
| `adapters/notion/integration/transforms.py` | 106 | Notion API ↔ UMH payload translations. |
| `adapters/notion/notion_publisher.py` | 485 | EOS Notion Publisher — canonical pattern for writing EOS content to Notion. |
| `adapters/notion/notion_sync.py` | 469 | Notion Sync — EOS runtime write layer. |

## adapters/scrapling/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/scrapling/__init__.py` | 0 | package marker (empty) |
| `adapters/scrapling/scrapling_connector.py` | 141 | ScraplingConnector — stealth HTTP fetching for EOS agents. |

## adapters/ssh/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/ssh/__init__.py` | 0 | package marker (empty) |
| `adapters/ssh/ssh_utils.py` | 136 | Centralized SSH/SCP utility — single entry point for all remote commands. |

## adapters/tailscale/ (2 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/tailscale/__init__.py` | 0 | package marker (empty) |
| `adapters/tailscale/tailscale_api.py` | 105 | Tailscale Admin API adapter. |

## adapters/tool_adapters/ (6 files)

| Path | Lines | Purpose |
|---|---|---|
| `adapters/tool_adapters/__init__.py` | 15 | Tool adapters — governed access to external systems (filesystem, shell, git, tmux). |
| `adapters/tool_adapters/base.py` | 50 | Base adapter — shared interface and deny-rule machinery. |
| `adapters/tool_adapters/filesystem.py` | 161 | Filesystem adapter — governed read/write/list/stat operations. |
| `adapters/tool_adapters/git.py` | 142 | Git adapter — governed git operations. Read-only by default. |
| `adapters/tool_adapters/shell.py` | 153 | Shell adapter — governed command execution with destructive-command blocking. |
| `adapters/tool_adapters/tmux.py` | 150 | Tmux adapter — governed session inspection. No killing by default. |
