# Phase 87A — Distributed Node Registry + Runtime Routing v1

**Date**: 2026-05-03
**Status**: Complete
**Extends**: Phase 87 (Leverage + Resource / Tool Taxonomy v1)
**Tests**: 146 passing (Phase 87A), 1413 total regression (Phase 80–87A)
**Safety**: 7 modules checked, 0 violations, 0 warnings
**Hard rules**: 20

## Executive Summary

Phase 87A introduces the Distributed Node Registry and Runtime Routing
advisory system — a typed taxonomy that models the user's multi-device
topology (VPS, Local PC, mobile, tablet, future cloud/GPU/edge/robotics)
and provides deterministic routing recommendations for where tasks should
execute.

Three doctrines govern the system:

1. **Distributed Runtime Doctrine** — UMH runs across multiple nodes, not
   just VPS. Each node has typed capabilities, roles, and availability.
2. **Node-Aware Routing Doctrine** — Tasks declare required capabilities
   and route to the safest valid node. Routing is advisory, not execution.
3. **Local Embodiment Doctrine** — Sources dependent on local browser
   sessions, logged-in accounts, or display default to Local PC, not VPS.

The system maps 25+ data sources from the Source Ingestion Map to their
required capabilities and node affinities. Instagram scraping → Local PC.
Docker services → VPS. ML training → GPU node. API calls → VPS preferred.

Integration with existing `umh/nodes/`, `umh/workstation/`, and
`umh/environments/` is strictly additive — no existing files modified.

Advisory-only. No execution. No mutation. No adapter calls. No LLM calls.
No network listeners. No secrets. Deterministic v1.

## Relationship to Existing Node Infrastructure

Phase 87A creates `umh/distributed/` as a new advisory taxonomy layer
that sits on top of three existing node/device abstractions:

| Module | Phase | Focus |
|--------|-------|-------|
| `umh/nodes/` (11 files) | Phase 14 | Execution: health, heartbeat, failover, SSH transport, daemon, worker |
| `umh/workstation/` (10 files) | Phase 77 | Operator: device registry, environment preferences, boot sequence |
| `umh/environments/` (11 files) | Phase 76 | Runtime: environment definitions, node models, capability gates |
| `umh/distributed/` (8 files) | **Phase 87A** | **Advisory: typed node taxonomy, capability mapping, routing policy** |

Phase 87A does NOT modify any existing module. It provides the advisory
layer that future phases can use to make routing decisions before
delegating to the existing execution infrastructure.

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `umh/distributed/__init__.py` | 5 | Package marker |
| `umh/distributed/contracts.py` | ~407 | 8 enums, 8 normalizers, 5 dataclasses, helpers |
| `umh/distributed/registry.py` | ~260 | 8 default node profiles, classify_node, active/future filters |
| `umh/distributed/capabilities.py` | ~331 | 15 default capabilities, 25+ source-to-capability mappings |
| `umh/distributed/routing.py` | ~355 | route_task_advisory, 6 default policies, affinity/capability matching |
| `umh/distributed/artifacts.py` | ~183 | 8 default sync policies, credential safety, classify_artifact |
| `umh/distributed/views.py` | ~261 | 6 UI-safe view types, converters, dashboard builder |
| `umh/distributed/safety.py` | ~191 | AST-based safety checking (imports, execution, listeners, secrets) |
| `tests/test_phase87a_distributed_node_registry.py` | ~954 | 146 tests across 12 test classes |

## Files Modified

| File | Change | Risk |
|------|--------|------|
| `docs/strategy/current_doctrine_index.md` | Added 3 new doctrines (Distributed Runtime, Node-Aware Routing, Local Embodiment) | LOW |
| `docs/strategy/war_sprint_context_manifest.md` | Updated Phase 87 status + added Phase 87A | LOW |
| `docs/strategy/source_ingestion_map.md` | Added 3 doctrine references in Governing Doctrines section | LOW |

## Enums (8)

| Enum | Count | Purpose |
|------|-------|---------|
| RuntimeNodeType | 9 | VPS, LOCAL_PC, MOBILE, TABLET, CLOUD_GPU, CLOUD_CPU, EDGE_DEVICE, ROBOTICS, UNKNOWN |
| NodeRole | 9 | PRIMARY_COMPUTE, DEVELOPMENT, LOCAL_EMBODIMENT, GPU_BURST, STORAGE_ARCHIVE, INGESTION, MONITORING, EDGE_SENSOR, UNKNOWN |
| NodeAvailability | 6 | ALWAYS_ON, ON_DEMAND, SCHEDULED, INTERMITTENT, FUTURE, UNKNOWN |
| CapabilityDomain | 16 | COMPUTE, STORAGE, NETWORK, GPU, BROWSER, FILESYSTEM, DOCKER, SSH, DISPLAY, AUDIO, CAMERA, LOCATION, BLUETOOTH, USB, LOCAL_ACCOUNTS, UNKNOWN |
| SourceAffinity | 8 | LOCAL_ONLY, VPS_ONLY, ANY_NODE, GPU_REQUIRED, BROWSER_REQUIRED, LOCAL_PREFERRED, VPS_PREFERRED, UNKNOWN |
| RoutingPriority | 7 | LATENCY, COST, RELIABILITY, PRIVACY, CAPABILITY, LOAD_BALANCE, UNKNOWN |
| ArtifactSyncDirection | 5 | LOCAL_TO_VPS, VPS_TO_LOCAL, BIDIRECTIONAL, NO_SYNC, UNKNOWN |
| ArtifactType | 9 | CODE, DATA, CONFIG, MODEL, MEDIA, LOG, CREDENTIAL, CACHE, UNKNOWN |

## Default Node Topology (8 nodes)

| Node | Type | Availability | Key Capabilities |
|------|------|-------------|------------------|
| Primary VPS | VPS | ALWAYS_ON | compute, storage, network, docker, ssh, filesystem |
| Local PC (Windows) | LOCAL_PC | INTERMITTENT | compute, storage, network, browser, display, audio, filesystem, local_accounts, usb |
| iPhone (Termius) | MOBILE | INTERMITTENT | ssh, display, camera, location, bluetooth, audio |
| iPad (code-server) | TABLET | INTERMITTENT | browser, display, network |
| Future Cloud GPU | CLOUD_GPU | FUTURE | compute, gpu, storage, network |
| Future Cloud CPU Burst | CLOUD_CPU | FUTURE | compute, storage, network, docker |
| Future Edge Devices | EDGE_DEVICE | FUTURE | network, bluetooth, location |
| Future Robotics Node | ROBOTICS | FUTURE | compute, camera, usb, bluetooth |

## Source Affinity Map (25+ sources)

| Affinity | Sources |
|----------|---------|
| LOCAL_ONLY | instagram, tiktok, twitter, linkedin, apple_notes, saved_videos, camera_capture, voice_notes |
| VPS_ONLY | docker_logs, claude_code_logs |
| VPS_PREFERRED | discord, telegram, obsidian, github |
| GPU_REQUIRED | model_training, media_rendering |
| ANY_NODE | youtube, gmail, google_drive, notion, stripe, calendly |
| LOCAL_PREFERRED | local_files, screenshots |

## Default Routing Policies (6)

| Policy | Priority | Affinity | Key Requirements |
|--------|----------|----------|------------------|
| Local Embodiment | PRIVACY | LOCAL_ONLY | browser + local_accounts |
| VPS Always-On Services | RELIABILITY | VPS_PREFERRED | docker |
| GPU Burst Compute | CAPABILITY | GPU_REQUIRED | gpu |
| API Integration | RELIABILITY | VPS_PREFERRED | network |
| Social Media Scraping | PRIVACY | LOCAL_ONLY | browser + local_accounts |
| File Processing | LATENCY | ANY_NODE | filesystem |

## Default Sync Policies (8)

| Artifact | Direction | Method |
|----------|-----------|--------|
| Code | BIDIRECTIONAL | Git push/pull via GitHub |
| Data | LOCAL_TO_VPS | Scheduled export transfer |
| Config | BIDIRECTIONAL | Git (excludes .env, *.key) |
| Model | VPS_TO_LOCAL | SCP/rsync |
| Media | LOCAL_TO_VPS | Scheduled transfer |
| Log | NO_SYNC | Stays on VPS |
| Credential | NO_SYNC | Each node has own .env |
| Cache | NO_SYNC | Node-local, rebuilt independently |

## Safety Validation

- **Modules checked**: 7 (all distributed/*.py except __init__)
- **Forbidden imports**: 0 (subprocess, requests, httpx, aiohttp, socket, selenium, playwright, smtplib, telegram, discord, paramiko)
- **Forbidden module prefixes**: 0 (umh.adapters, umh.execution, umh.governance, umh.memory, umh.storage)
- **Execution patterns**: 0 (execute, run_action, send_message, post, delete, create_resource, mutate, promote_memory)
- **Network listener patterns**: 0 (bind, listen, serve, accept, start_server, run_server)
- **Secret patterns**: 0 (os.getenv, load_dotenv, os.environ)

## Tests

| Class | Tests | Covers |
|-------|-------|--------|
| TestContractEnums | 14 | All 8 enums, UNKNOWN fallback, member counts |
| TestContractNormalizers | 11 | All 8 normalizers + unknown degradation |
| TestContractHelpers | 5 | _dist_id format/uniqueness, clamp_score bounds |
| TestContractSerialization | 5 | All 5 dataclass to_dict/from_dict round-trips |
| TestRegistry | 19 | 8 defaults, classify_node, active/future filters, uniqueness |
| TestCapabilities | 20 | 15 defaults, source mapping, affinity, classify_capability |
| TestRouting | 16 | Affinity enforcement, capability matching, policies, fallback |
| TestArtifacts | 15 | 8 sync policies, credential safety, classify_artifact |
| TestViews | 7 | 6 view converters + dashboard builder + no sensitive data |
| TestSafety | 10 | Module scan, fixture detection (imports, execution, listeners, secrets), recommendation safety |
| TestLayering | 9 | Per-file forbidden import checks + no model_router + no LLM calls |
| TestIntegration | 5 | Phase 86/87 import compat, existing nodes/workstation unmodified |
| TestPhase87ARegression | 9 | Phase 80–87A import smoke tests |
| **Total** | **146** | |

## Regression

- **Phase 87A tests**: 146/146 passing
- **Phase 80–87A regression**: 1413/1413 passing
- **Phase 87 tests**: 118/118 passing (unchanged)
- **Phase 86 tests**: 81/81 passing (unchanged)
- **Safety validation**: 7 modules, 0 violations

## Known Limitations

- Advisory only — no execution
- Deterministic routing — no ML/LLM enhancement
- No live telemetry integration (existing `umh/nodes/` has that)
- No live health checks (existing `umh/nodes/health.py` has that)
- No actual file sync execution (policies are advisory)
- No actual network probing or device detection
- Default nodes are static — no dynamic discovery
- Registry/observability/API/CLI integration deferred

## Is Phase 88 Template System Safe?

Yes. Phase 88 can safely build on Phase 87A:
- Node profiles inform what devices templates need to target
- Capability mappings tell templates what's available where
- Routing policies can recommend which node to execute a templated workflow on
- Sync policies inform template outputs about artifact distribution
- No Phase 87A code needs modification — Phase 88 extends, not changes
