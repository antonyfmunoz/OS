# Phase 96.8AT — Exploratory Environment Mapping Engine

## Summary

Built a pre-ingestion environment discovery layer that maps the founder's
Windows workstation before any ingestion executes. Establishes the pattern:
explore → map → classify → plan → ingest.

## What was built

### Core engine
- `core/workstation/environment_mapping_engine_v1.py`
  - 20 discovery domains (browsers, messaging, productivity, dev tools, etc.)
  - 15 platform→process mappings for process-based detection
  - Dataclasses: DiscoveredPlatform, DiscoveredAccount, DiscoveredWorkspace,
    RelationshipEdge, IngestionLane, EnvironmentTopology
  - Relationship synthesis with order-independent canonical_key dedup
  - Ingestion lane planner with per-platform extraction method selection
  - Canonical/instance separation with keyword scoring (instance default)
  - L0-L3 environment maturity model (string-based, parallel to actuator L0-L7)
  - Hard maturity ceilings (no screenshots→L1, no graph/relationships/lanes/founder→L2)
  - Proof persistence to `data/runtime/workstation_relay/environment_maps/`

### Command registration (5 files)
- `core/registry/canonical_command_registry_v1.py` — `!explore-environment` CommandEntry
- `core/control_plane_router/router_contracts.py` — ENVIRONMENT_DISCOVERY CapabilityType, ALLOWED_ACTION_TYPES
- `core/control_plane_router/control_plane_router_v1.py` — ACTION_CAPABILITY_MAP entry
- `core/environment_bridge/windows_desktop_adapter_contracts.py` — EXPLORE_ENVIRONMENT enum value
- `config/control_plane_router_v1.json` — allowed_action_types updated
- `data/registries/local_worker_adapter_registry_v1.json` — adapter capability added

### Windows relay
- `scripts/windows_interactive_desktop_relay.ps1` — Handle-ExploreEnvironment function
  - 7 stages: process enumeration, installed apps, Chrome profiles, browser sessions,
    local workspaces, desktop screenshot, taskbar screenshot
  - All discovery from public system data (no credential scraping)

### Discord handler
- `services/handlers/substrate_command_handler.py` — `!explore-environment` intercept
  - Three-gate architecture (relay health, SSH transport, transport completion)
  - Founder confirmation required before proof generation
  - Discord output with discovery counts and maturity assessment

## Test results

74 tests across 23 test classes. All passing.

Test classes:
- TestDiscoveredPlatform(2), TestDiscoveredAccount(2), TestDiscoveredWorkspace(2)
- TestRelationshipEdge(3), TestDuplicateRelationshipSuppression(2)
- TestCanonicalLeakagePrevention(4), TestInstanceLeakagePrevention(3)
- TestPlatformClassification(4), TestGraphIntegrity(5)
- TestLanePlannerCorrectness(5), TestReplayDeterminism(2)
- TestStaleRelayBlocked(1), TestDryRunBlocked(3)
- TestMaturityClassification(5), TestHardCeilings(7)
- TestEvidenceExtraction(3), TestProcessExtraction(3)
- TestAccountExtraction(3), TestProofPersistence(4)
- TestProofSerialization(2), TestFullPipeline(4)
- TestDiscoveryDomains(1), TestTransportIntegration(1)
- TestRegistryIntegration(3)

## Regression

1181/1181 substrate tests passing (including 10 registry count fixes
for the new 14-command registry).

## Maturity levels

| Level | Name | Requirements |
|-------|------|-------------|
| L0 | NO_MAPPING | No discovery data |
| L1 | PROCESSES_ENUMERATED | Process list captured |
| L2 | PLATFORMS_IDENTIFIED | Platforms identified, accounts linked |
| L3 | ENVIRONMENT_INTELLIGENCE | Full topology with relationships, lanes, screenshots, founder confirmation |

## Hard ceilings

| Missing evidence | Maximum maturity |
|-----------------|-----------------|
| No screenshots | L1 |
| No topology graph | L2 |
| No relationships | L2 |
| No ingestion lanes | L2 |
| No founder confirmation | L2 |

## Date
2026-05-09
