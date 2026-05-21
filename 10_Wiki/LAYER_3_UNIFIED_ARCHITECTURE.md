---
status: CANONICAL — Layer 3 Unified Architecture
promoted: 2026-05-21
q1_implementation_commit: ebcf068b
q2_q6_status: RESOLVED (direction confirms, no Phase 1 work)
predecessor_draft: /tmp/layer3_unified_architecture.md
---

# Layer 3 — Unified Adapter Architecture

Supersedes: /tmp/layer3_design_recon.md (partially invalidated by architectural corrections 2026-05-20).

Author: Developer Agent + AFM  
Date: 2026-05-20  
Status: CANONICAL — promoted 2026-05-21, all 6 open questions resolved

---

## 0. Architectural Corrections Applied

This document incorporates the 10 corrections from the Layer 3 alignment session:

1. **MODEL**: cc_sdk (Max subscription, Opus 4.6, no per-call cost) is default for decomposition
2. **ADAPTERS**: General connection layer. Bidirectionality is inherited from (tool × modality), not a design choice
3. **MODALITIES**: API, Computer Use, Filesystem, Direct DB — composable per adapter
4. **SOCKET-SUBTYPE**: Socket pattern = specific subtype for ecosystem participants (Trinity). Not the general pattern
5. **UNIFIED PIPELINE**: One canonical pipeline (perceive→interpret→decompose→bridge→map→persist→query_back). Sockets add capabilities+outcomes ON TOP for ecosystem participants only
6. **CAPABILITY DISCOVERY**: Multi-source — API introspection, vendor docs, internet research, operational testing
7. **ADAPTER MATURITY**: Measurable property per adapter. Starts low, grows toward masterful
8. **ONBOARDING FLOW**: Post-install setup for mass-market. Automated diagnostic → auto-create adapters → build world model
9. **10_Wiki**: IS the memory system. Leverage principle = no redundancy with canonical_memory_store
10. **TRINITY**: EOS, LyfeOS, CreatorOS are ecosystem participants (socket subtype). Generic external tools use general adapter pattern

---

## 0.5 Leverage Principle (System Architecture Rule)

The Leverage Principle governs how OST integrates external code, patterns, and frameworks:

1. **System sovereignty.** OST never hardcodes external IP, framework names, or source attribution into system text — architecture docs, code, agent souls, prompts, skill files, or any other system-level artifact. The system describes itself in OST-native terms from first principles.

2. **External IP lives in the memory layer.** External frameworks and branded methodologies are KNOWLEDGE the system has via CORPUS/CANON/SCHEMA. Agents can reference and apply external wisdom because that wisdom lives in memory. The system's identity, code, and architecture do not reference any specific external source by name.

3. **Live leverages wrapped behind OST-native interfaces.** Any external code OST imports and runs is wrapped behind an interface that's not source-specific, so the implementation can swap (leverage → ownership) without disturbing callers.

4. **Operational tracking.** Live external code dependencies are tracked in the Ownership Roadmap with source, integration state, and migration trigger. Absorbed patterns (no live code dep) require no tracking.

---

## 0.6 Ownership Principle (Instance Policy)

Operator instance policy. For this instance:

1. Every live leverage has an ownership trajectory tracked in the Ownership Roadmap.
2. Ownership = same capability, OST-native implementation, no external dependency.
3. Migration triggers are documented per entry (scale, security, customization, principle).
4. Entries may explicitly state "no planned migration" — that's a real choice with consequences, documented openly.

---

## 1. Memory Architecture — The Three-Layer Model

Pipeline verbs (perceive, interpret, decompose) describe what the canonical pipeline DOES; CORPUS / CANON / SCHEMA describe the layered memory it FEEDS. Naming separates pipeline verbs from storage layers.

### 1.1 Hypothesis Confirmed

WIKI_RULES.md explicitly declares the `CORPUS → CANON → SCHEMA` pattern. The existing codebase implements two of three layers. Layer 3 formalizes the full stack.

### 1.2 Layer Definitions

```
┌─────────────────────────────────────────────────────────────┐
│  SCHEMA (structured types, queryable entities)              │
│  ─ domain_projection entries in canonical_memory_store      │
│  ─ future: typed entity tables, knowledge graph edges       │
│  ─ machine-queryable, API-surfaced                          │
├─────────────────────────────────────────────────────────────┤
│  CANON (curated knowledge pages)                            │
│  ─ 10_Wiki/ — 205 curated pages (concept/entity/decision/  │
│    synthesis/source), [[wikilinks]], YAML frontmatter       │
│  ─ human-readable, LLM-navigable via index.md + palace      │
│  ─ THE authoritative knowledge layer for UMH sessions       │
├─────────────────────────────────────────────────────────────┤
│  CORPUS (immutable ingested material)                       │
│  ─ 01_Inbox/ — human-generated signals + notes              │
│  ─ canonical_memory_store — LLM-decomposed observations     │
│    (63 entries: observations, projections, instances)        │
│  ─ data/ — runtime data, audits, proofs                     │
│  ─ docs/ — reference documentation                          │
│  ─ NEVER modified after creation                            │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Data Flow

```
Adapter → canonical pipeline → CORPUS (canonical_memory_store)
                                    │
                          curation/promotion (manual or LLM-assisted)
                                    │
                                    ▼
                            CANON (10_Wiki/)
                                    │
                          entity extraction (future)
                                    │
                                    ▼
                          SCHEMA (domain projections, typed entities)
```

### 1.4 Leverage Principle (No Redundancy)

- `canonical_memory_store` and `10_Wiki/` are NOT competing stores. They are adjacent layers.
- CORPUS observations are machine-generated, high-volume, append-only.
- CANON pages are curated, low-volume, editable.
- A CORPUS observation may be *promoted* to a CANON page. The observation persists in CORPUS (immutable). The CANON page is the authoritative, human-readable form.
- The existing WIKI_RULES.md ingestion rules (lines 127-137) already describe this promotion: read CORPUS → create source page → extract concepts/entities → link.
- Missing: automated promotion pipeline (CORPUS → CANON). Currently manual. Phase 6 builds this.

### 1.5 The 10_Wiki/codebase/ Problem

5,804 of 6,032 .md files in 10_Wiki/ are auto-generated codebase docs, not curated knowledge. These belong in a separate surface (e.g., `data/codebase_docs/` or a separate index). They dilute wiki signal. Migration recommendation:

- Move `10_Wiki/codebase/` → `data/codebase_docs/`
- Or: gate them behind a separate index entry (`codebase_index.md`) that the palace doesn't traverse
- Decision deferred: this is a wiki maintenance task, not a Layer 3 blocker

---

## 2. Adapter Framework

### 2.1 Modality as First-Class Concept

Modality describes HOW an adapter communicates with its target. Currently implicit — used in practice but not typed in code.

```python
class ModalityType(str, Enum):
    """How an adapter communicates with its external target."""
    API = "api"                   # HTTP/REST/GraphQL calls
    COMPUTER_USE = "computer_use" # Browser automation (Playwright wrapper)
    FILESYSTEM = "filesystem"     # Local/remote file read/write
    DIRECT_DB = "direct_db"       # SQL connections (psycopg2, etc.)
```

**Composition rule**: A single adapter MAY use multiple modalities. Example: a Google Drive adapter uses API (Drive API for metadata/permissions) + Filesystem (local sync folder reads). The modalities compose — the adapter declares which ones it uses.

```python
@dataclass
class AdapterManifest:
    """Universal adapter descriptor. Replaces scattered descriptor types."""
    adapter_id: str
    adapter_type: str               # e.g., "notion", "google_drive", "obsidian"
    modalities: list[ModalityType]   # which communication paths this adapter uses
    participant_type: ParticipantType  # ECOSYSTEM or EXTERNAL
    capabilities: list[CapabilityDescriptor]
    maturity: AdapterMaturity        # current maturity snapshot
    health: AdapterHealthRecord      # operational state (from lifecycle manager)
    version: str = "v1"
```

### 2.2 Participant Types

```python
class ParticipantType(str, Enum):
    """Whether an adapter is an ecosystem participant or external tool."""
    ECOSYSTEM = "ecosystem"  # Trinity: EOS, LyfeOS, CreatorOS
    EXTERNAL = "external"    # Everything else: Notion, Drive, Obsidian, GitHub, etc.
```

- **ECOSYSTEM** adapters use the socket-pipeline pattern (services/umh/integrations/). They get: signal emission, capability handling, outcome writeback, view frames, correlation tracking.
- **EXTERNAL** adapters use the general adapter pattern. They get: canonical ingestion pipeline (perceive→decompose→persist), capability discovery, maturity tracking. They do NOT get socket wiring unless promoted to ecosystem.

### 2.3 The Unified Pipeline

Every adapter, regardless of participant type, flows through the canonical ingestion pipeline:

```
adapter.read() → Source protocol → GenericIngestionOrchestrator
                 └─ perceive → interpret → decompose → bridge → map → persist → query_back
```

Ecosystem participants additionally get:

```
adapter → SignalSocket → ExecutionPipeline → CapabilitySocket → OutcomeSocket → ViewSocket
```

This is NOT a separate path. The execution pipeline handles capability dispatch and outcome writeback. The ingestion pipeline handles knowledge extraction. An ecosystem participant may use both simultaneously.

### 2.4 Adapter Catalog (Current + Planned)

| Adapter | Modalities | Participant | Status | Notes |
|---------|-----------|-------------|--------|-------|
| EOS | Direct DB | ECOSYSTEM | LIVE | Socket pattern, psycopg2, polled |
| Notion | API | EXTERNAL (legacy ECOSYSTEM) | LIVE | Socket pattern, migration candidate |
| Filesystem | Filesystem | EXTERNAL | LIVE | BaseAdapter subclass, safe-root enforcement |
| Shell | Filesystem | EXTERNAL | LIVE | BaseAdapter subclass, command execution |
| LocalFile | Filesystem | EXTERNAL | LIVE | Source protocol only (ingestion) |
| GWS | API | EXTERNAL | LIVE | Source protocol only (ingestion) |
| GitHub | API + Filesystem | EXTERNAL | PARTIAL | scripts/github_trinity_ingest.py, not wired to adapter registry |
| Obsidian | Filesystem | EXTERNAL | PLANNED | Local vault read, wikilink-aware |
| Google Drive | API + Filesystem | EXTERNAL | PLANNED | OAuth + local sync folder |
| Windows Dev | Filesystem + CU | EXTERNAL | PLANNED | Tailscale-bridged, remote file access |
| VPS Runtime | Filesystem + Direct DB | EXTERNAL | PLANNED | Local state, Docker introspection |

### 2.5 Notion Migration Path

Notion currently lives in `services/umh/integrations/notion/` using the full socket pattern (7 files). It is NOT an ecosystem participant — it's a generic external tool that was wired with the socket pattern for convenience.

Migration plan:
1. Notion continues to work as-is. No breaking changes.
2. Its `ParticipantType` is set to `EXTERNAL` in the new AdapterManifest.
3. The socket wiring remains functional — EXTERNAL adapters CAN use sockets, they're just not required to.
4. Over time, as the general adapter pattern matures, Notion's ingestion shifts from custom poller → canonical pipeline with Notion Source.

---

## 3. Adapter Maturity (Unified, All-Modality)

### 3.1 Problem with Current State

`actuator_maturity_v1.py` defines L0-L7 levels but they're GUI-specific (chrome_pid, window_handle, screenshot_path). No general adapter maturity model exists.

`adapter_lifecycle_manager_v1.py` tracks operational health (AVAILABLE/BUSY/DEGRADED/OFFLINE) but not knowledge depth.

These are orthogonal concerns:
- **Maturity** = how well UMH *understands* what an adapter can do (knowledge depth)
- **Health** = whether the adapter is currently operational (runtime state)

### 3.2 Unified Maturity Model

```python
class AdapterMaturityLevel(IntEnum):
    """How well UMH understands an adapter's capabilities. Modality-agnostic."""
    L0_REGISTERED = 0      # Adapter declared, no capabilities known
    L1_CONNECTED = 1       # Connection verified (auth works, endpoint responds)
    L2_CAPABILITIES_KNOWN = 2  # Capability list populated (API introspection or doc absorption)
    L3_TESTED = 3          # At least one capability exercised successfully
    L4_EDGE_CASES_MAPPED = 4   # Known failure modes, rate limits, error shapes documented
    L5_OPTIMIZED = 5       # Retry strategies, caching, batching tuned from operational experience
    L6_EXPERT = 6          # Full vendor doc corpus absorbed, edge cases from real usage cataloged
    L7_MASTERFUL = 7       # Replayable patterns, can teach other agents, generates new strategies
```

### 3.3 Maturity Dimensions

Each level is computed from evidence across 4 dimensions:

| Dimension | What it measures | Evidence sources |
|-----------|-----------------|-----------------|
| **Capability coverage** | % of known capabilities exercised | Operational logs |
| **Doc absorption** | % of vendor documentation ingested | TME research agent reports |
| **Operational experience** | Success/failure ratio over time | Lifecycle manager metrics |
| **Edge case knowledge** | Documented failure modes, workarounds | Gotchas catalog per adapter |

```python
MATURITY_REQUIREMENTS: dict[AdapterMaturityLevel, dict[str, bool]] = {
    AdapterMaturityLevel.L0_REGISTERED: {},
    AdapterMaturityLevel.L1_CONNECTED: {"auth_verified": True},
    AdapterMaturityLevel.L2_CAPABILITIES_KNOWN: {"auth_verified": True, "capability_count_gt_0": True},
    AdapterMaturityLevel.L3_TESTED: {"auth_verified": True, "capability_count_gt_0": True, "successful_execution_count_gt_0": True},
    AdapterMaturityLevel.L4_EDGE_CASES_MAPPED: {"auth_verified": True, "capability_count_gt_0": True, "successful_execution_count_gt_0": True, "failure_modes_documented": True},
    AdapterMaturityLevel.L5_OPTIMIZED: {"auth_verified": True, "capability_count_gt_0": True, "execution_count_gt_10": True, "retry_strategy_configured": True},
    AdapterMaturityLevel.L6_EXPERT: {"auth_verified": True, "doc_absorption_gt_80pct": True, "execution_count_gt_50": True, "gotchas_catalog_exists": True},
    AdapterMaturityLevel.L7_MASTERFUL: {"auth_verified": True, "doc_absorption_gt_90pct": True, "execution_count_gt_100": True, "replayable_patterns_exist": True, "teaching_artifacts_exist": True},
}
```

### 3.4 Migration from Actuator Maturity

`actuator_maturity_v1.py` is NOT replaced. It remains as a CU-specific evidence model for GUI actuation. The new `AdapterMaturityLevel` wraps it:

- For CU-modality adapters: actuator maturity evidence contributes to the `operational_experience` dimension
- For API/Filesystem/DB adapters: actuator maturity is irrelevant — their evidence comes from different sources
- Both share the same L0-L7 scale so maturity is comparable across adapter types

---

## 4. Capability Discovery (Unified)

### 4.1 Existing Assets

The TME (Tool Mastery Engine) research agent in `composition/mastery/research/` already implements vendor doc discovery and absorption:

- `source_discovery.py` — builds prioritized source lists from registry + MCP manifests
- `docs_site_discovery.py` — probes /sitemap.xml, /llms.txt for doc URLs
- `headless_fetcher.py` — Playwright headless rendering for SPA doc sites
- `structured_crawl.py` — crawls approved doc URLs
- `github_extractor.py` — extracts from GitHub repos

This IS the LLM-on-docs primitive. Currently wired for TME skill creation, not adapter capability discovery. Needs generalization.

### 4.2 Unified Capability Discovery Pipeline

```
                     ┌──────────────────────┐
                     │  Capability Discovery │
                     │      Orchestrator     │
                     └────────┬─────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
    ┌─────▼─────┐     ┌──────▼──────┐    ┌──────▼──────┐
    │    API     │     │   Vendor    │    │ Operational │
    │Introspect  │     │    Docs     │    │   Testing   │
    │            │     │  (TME reuse)│    │             │
    └─────┬─────┘     └──────┬──────┘    └──────┬──────┘
          │                   │                   │
          ▼                   ▼                   ▼
    Interrogate        Absorb docs via       Exercise each
    connection:        TME pipeline:         capability:
    - OpenAPI spec     - sitemap probe       - dry-run mode
    - GraphQL schema   - llms.txt            - error shape
    - /capabilities    - headless render     - rate limit
    - REST discovery   - content extraction    discovery
          │                   │                   │
          └───────────────────┼───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │ Capability Catalog │
                    │  (per adapter)     │
                    │                    │
                    │ capabilities: []   │
                    │ gotchas: []        │
                    │ maturity_evidence  │
                    └───────────────────┘
```

### 4.3 Source-Specific Discovery Methods

| Discovery Source | Method | Adapters That Benefit |
|-----------------|--------|----------------------|
| **API introspection** | OpenAPI/GraphQL schema fetch, endpoint enumeration | Notion, Drive, GitHub, any REST API |
| **Vendor docs** (TME reuse) | sitemap probe → doc crawl → LLM extraction | All — every tool has docs |
| **Internet research** | Web search for "{tool} API capabilities" | New/unfamiliar tools |
| **Operational testing** | Execute capability, record success/failure/error shape | All — evidence-based maturity |
| **Connection interrogation** | Tool-specific: Notion `/search`, Drive `/files`, GitHub `/repos` | API-modality adapters |

### 4.4 TME Generalization Plan

The TME research agent currently:
1. Takes a tool slug → builds source plan → fetches docs → extracts knowledge → writes skill file

Generalize to:
1. Takes an adapter_id → builds source plan → fetches docs → extracts CAPABILITIES → writes capability catalog
2. Same pipeline, different output target (capability catalog vs skill file)
3. The `SourceRef`, `SourcePlan`, `SourceTier` models are reusable as-is
4. `source_discovery.py` needs an adapter-focused entry point alongside the tool-focused one
5. `docs_site_discovery.py` and `headless_fetcher.py` are reusable unchanged

---

## 5. Environmental Diagnostic (Operationalized)

### 5.1 Existing State

`environment_mapping_engine_v1.py` defines:
- 20 discovery domains (chrome_profiles → installed_desktop_apps)
- `DiscoveredPlatform`, `EnvironmentTopology`, `IngestionLane` dataclasses
- Gated on "visible foreground CU + relay transport" — not operational without GUI

### 5.2 Operationalization Strategy

The environment mapping engine assumes GUI-first discovery. Layer 3 adds headless/API/shell discovery paths so the diagnostic runs on a VPS with no display.

**Three discovery tiers:**

| Tier | Method | Domains Covered | Requires |
|------|--------|----------------|----------|
| **T1: Shell enumeration** | `which`, `dpkg -l`, `pip list`, process list, filesystem scan | local_repos, docker_containers, terminals, vscode, installed_desktop_apps, startup_apps, obsidian, local_vaults | Linux shell only |
| **T2: API probing** | OAuth token check, endpoint ping, account listing | google_accounts, github, notion, discord, slack, gmail, drive, claude, openai | Credentials in .env |
| **T3: Browser automation** | CU agent navigates web UIs, reads account settings | chrome_profiles, browser_sessions, any tool without API | CU harness + display or headless Chrome |

**Execution order:** T1 → T2 → T3 (cheapest first, most expensive last). Each tier contributes to the same `EnvironmentTopology` output.

### 5.3 OSS Browser Harness Recommendation: browser-use

**Decision: Adopt `browser-use` (MIT, Python, ~79k stars) as the CU modality harness.**

Evaluation of 5 candidates:

| Candidate | Language | Wraps Playwright | Python SDK | Headless VPS | Active 2026 | Verdict |
|-----------|----------|-----------------|------------|-------------|-------------|---------|
| **browser-use** | Python | Yes | Native | Yes | Yes | **SELECTED** |
| Stagehand | TypeScript | No (CDP in v3) | Thin port | Yes | Yes | Python port lags |
| AgentQL | Python | Yes | Yes | Yes | Yes | Query tool, not agent loop |
| LaVague | Python | Optional | Yes | Partial | Stale | Skip — low activity |
| Browserbase | Cloud | N/A | Via Stagehand | Cloud only | Yes | Vendor lock-in |

**Justification:**
- **Python-native** — fits our stack (Python 3.12)
- **Wraps Playwright** — we already depend on Playwright for headless_fetcher.py
- **Full agent loop** — task in → browser actions → result. AI decides next action based on page state
- **MIT license** — no vendor lock-in
- **Headless VPS** — runs on our Linux VPS without display
- **Vision + DOM** — supports both structured DOM extraction and screenshot-based reasoning

**Integration approach:**
- Wire `browser-use` agent loop through `model_router.call_with_fallback()` so it uses cc_sdk (Opus) for decision-making
- The existing Playwright install becomes the browser backend for both headless_fetcher (doc fetching) and browser-use (CU actuation)
- AgentQL is worth tracking as a complementary perception primitive (structured page extraction) but is NOT the primary harness

### 5.4 T1 Shell Enumeration (New, Unbuilt)

```python
# Conceptual — not final code
class ShellDiagnostic:
    """Discover local environment via shell commands. No GUI required."""

    def discover_repos(self) -> list[RepoInfo]:
        """find / -name .git -type d -maxdepth 5"""

    def discover_docker(self) -> list[ContainerInfo]:
        """docker ps -a --format json"""

    def discover_installed_tools(self) -> list[ToolInfo]:
        """which + dpkg -l + pip list + npm list -g"""

    def discover_obsidian_vaults(self) -> list[VaultInfo]:
        """find / -name .obsidian -type d -maxdepth 5"""

    def discover_vscode_workspaces(self) -> list[WorkspaceInfo]:
        """~/.config/Code/User/workspaceStorage/"""

    def discover_running_services(self) -> list[ServiceInfo]:
        """systemctl list-units + docker ps + ps aux | grep python"""
```

### 5.5 T2 API Probing (New, Partially Exists)

Some API probing already exists implicitly:
- `notion/auth.py` — `get_notion_client()` verifies Notion token
- `eos/manifest.py` — `load_eos_config()` checks EOS_DATABASE_URL
- `gws_source.py` — GWSDocumentScanner verifies Google auth

Generalize: for each `.env` credential, attempt connection → record success/failure → populate EnvironmentTopology.

### 5.6 Network Discovery (Future, Not Phase 1)

- mDNS/Bonjour scan for local services
- Tailscale peer list for cross-device discovery
- Not needed for initial deployment — shell + API covers the VPS case

---

## 6. Onboarding Flow

### 6.1 Current State

Entirely unbuilt. No onboarding orchestrator, no setup wizard, no automated diagnostic trigger.

### 6.2 Design: Post-Install Orchestrator

The onboarding flow runs once (or re-runs on demand) and bootstraps UMH's world model.

```
┌─────────────────────────────────────────────────────────┐
│                  Onboarding Orchestrator                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. IDENTITY SETUP                                      │
│     ├─ "What should I call you?" → user_name            │
│     ├─ "What should I call myself?" → ai_name           │
│     └─ Writes to BIS (business instance state)          │
│                                                         │
│  2. ENVIRONMENT DIAGNOSTIC                              │
│     ├─ T1: shell enumeration (immediate)                │
│     ├─ T2: API probing (if credentials found)           │
│     ├─ T3: browser scan (if CU available)               │
│     └─ Produces EnvironmentTopology                     │
│                                                         │
│  3. ADAPTER AUTO-CREATION                               │
│     ├─ For each discovered platform:                    │
│     │   ├─ Create AdapterManifest (L0_REGISTERED)       │
│     │   ├─ If credentials found → verify → L1_CONNECTED │
│     │   └─ If API available → introspect → L2_CAPABLE   │
│     └─ Register all adapters in AdapterRegistry         │
│                                                         │
│  4. CAPABILITY BOOTSTRAP                                │
│     ├─ For each L1+ adapter:                            │
│     │   ├─ Run capability discovery (TME pipeline)      │
│     │   └─ Populate capability catalog                  │
│     └─ Background: continues growing maturity           │
│                                                         │
│  5. INITIAL INGESTION                                   │
│     ├─ For each adapter with readable content:          │
│     │   ├─ Ingest via canonical pipeline → CORPUS       │
│     │   └─ High-value items → prompt CANON promotion    │
│     └─ Produces initial world model in memory store     │
│                                                         │
│  6. PROFILE GENERATION                                  │
│     ├─ Synthesize user profile from ingested content    │
│     ├─ Store as CANON entity page                       │
│     └─ "Here's what I've learned about your setup..."   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 6.3 Mass-Market UX Principles

- **Feels like the system figures itself out.** User provides credentials, system discovers everything else.
- **Smart defaults.** If only one Obsidian vault found → use it. If one Google account → use it. No confirmation dialogs for unambiguous cases.
- **Progressive disclosure.** Show summary of what was found, not 200-line log. User can drill into details.
- **No 30-step wizard.** The onboarding is: name yourself → name me → (automated work happens) → "here's what I found, anything I missed?"
- **Re-runnable.** `umh diagnostic --full` reruns the whole thing, updates adapters, finds new platforms.

---

## 7. Migration Paths

### 7.1 Scattered Components → Unified Targets

| Current Component | Location | Unified Target | Migration Type |
|---|---|---|---|
| `ActuatorMaturityLevel` (L0-L7) | `execution/actuation/actuator_maturity_v1.py` | Remains as CU-specific evidence model. New `AdapterMaturityLevel` wraps it. | Compose (not replace) |
| TME research agent | `composition/mastery/research/` | Generalized `CapabilityDiscoveryOrchestrator`. Same pipeline, adapter-focused output. | Generalize entry point |
| Environment mapping engine | `execution/workers/workstation/environment_mapping_engine_v1.py` | Operationalized `EnvironmentDiagnostic` with T1/T2/T3 tiers. Reuses dataclasses. | Add tiers, remove GUI gate |
| Notion socket integration | `services/umh/integrations/notion/` | Continues as-is. `ParticipantType.EXTERNAL`. Socket wiring optional. | Type annotation only |
| EOS socket integration | `services/umh/integrations/eos/` | Continues as-is. `ParticipantType.ECOSYSTEM`. | Type annotation only |
| `AdapterDescriptor` / `AdapterRegistry` | `adapters/adapter_engine/adapter_registry_contracts.py` | Extended with `modalities` and `participant_type` fields. | Additive fields |
| `AdapterLifecycleManager` | `adapters/adapter_engine/adapter_lifecycle_manager_v1.py` | Continues as health tracker. Separate from maturity. | No change |
| `Source` protocol | `understanding/perception/source.py` | Unchanged. Every adapter produces Sources for ingestion. | No change |
| `10_Wiki/codebase/` (5,804 auto-docs) | `10_Wiki/codebase/` | Move to `data/codebase_docs/` or gate behind separate index. | Deferred maintenance |
| `headless_fetcher.py` | `composition/mastery/research/headless_fetcher.py` | Shared Playwright backend with browser-use. No code change. | Configuration only |

### 7.2 What Does NOT Move

- `services/umh/sockets/` — stays as-is. The socket abstraction (SignalSocket, CapabilitySocket, OutcomeSocket, ViewSocket) is correct for ecosystem participants.
- `services/umh/control_plane/` — stays as-is. Integration registration wiring is correct.
- `canonical_memory_store` — stays as CORPUS layer. Not migrated.
- `runtime/ingestion/` — stays as canonical pipeline. Not migrated.

---

## 8. Implementation Phasing

### Phase 1: Type System Foundation
**Goal**: Formalize Modality + ParticipantType as first-class types.  
**Scope**: New enum + dataclass definitions. Annotate existing adapters. No behavioral changes.  
**Files**:
- New: `adapters/adapter_engine/modality.py` (ModalityType enum)
- New: `adapters/adapter_engine/participant.py` (ParticipantType enum)
- New: `adapters/adapter_engine/adapter_manifest.py` (AdapterManifest dataclass)
- Edit: `adapters/adapter_engine/adapter_registry_contracts.py` (extend AdapterDescriptor)
- New: tests for type validation  
**Dependencies**: None  
**Risk**: LOW — additive type definitions only  
**Merge target**: `main`

### Phase 2: Generalized Adapter Maturity
**Goal**: Replace GUI-only maturity with all-modality maturity model.  
**Scope**: New `AdapterMaturityLevel` enum + evidence model. Wire to lifecycle manager.  
**Files**:
- New: `adapters/adapter_engine/adapter_maturity.py`
- Edit: `adapters/adapter_engine/adapter_lifecycle_manager_v1.py` (add maturity field to health record)
- `actuator_maturity_v1.py` unchanged (CU-specific, now a sub-evidence source)
- New: tests  
**Dependencies**: Phase 1 (uses AdapterManifest)  
**Risk**: LOW — new module, existing code untouched

### Phase 3: Generalized Capability Discovery
**Goal**: Repurpose TME research pipeline for adapter capability discovery.  
**Scope**: New orchestrator that calls existing TME primitives with adapter-focused output.  
**Files**:
- New: `adapters/adapter_engine/capability_discovery.py` (CapabilityDiscoveryOrchestrator)
- Edit: `composition/mastery/research/source_discovery.py` (add adapter_id entry point alongside tool slug)
- Reuse: `docs_site_discovery.py`, `headless_fetcher.py`, `structured_crawl.py` unchanged
- New: `adapters/adapter_engine/capability_catalog.py` (per-adapter capability + gotchas store)
- New: tests  
**Dependencies**: Phase 2 (maturity evidence feeds from discovery)  
**Risk**: MEDIUM — modifying TME entry point, must not break existing skill creation

### Phase 4: Operationalized Environmental Diagnostic
**Goal**: Environment diagnostic that runs on VPS without GUI.  
**Scope**: T1 (shell) and T2 (API) diagnostic tiers. T3 (CU harness) added behind feature flag.  
**Files**:
- New: `adapters/adapter_engine/environment_diagnostic.py` (ShellDiagnostic, ApiProber)
- New: `adapters/adapter_engine/browser_harness.py` (CU harness wrapper, model_router integration)
- Edit: `environment_mapping_engine_v1.py` (wire diagnostic tiers into existing dataclasses)
- Add dependency: `browser-use` to requirements.txt (behind optional extra)
- New: tests  
**Dependencies**: Phase 3 (capability discovery populates adapters found by diagnostic)  
**Risk**: MEDIUM — new external dependency (browser-use), system-level shell commands

### Phase 5: Onboarding Orchestrator
**Goal**: Post-install flow that bootstraps world model automatically.  
**Scope**: CLI + API endpoint. Chains: identity → diagnostic → adapter creation → capability bootstrap → initial ingestion.  
**Files**:
- New: `services/umh/onboarding/orchestrator.py`
- New: `services/umh/onboarding/identity_setup.py`
- Edit: `services/umh/control_plane/app.py` (add /api/umh/onboarding endpoint)
- New: tests  
**Dependencies**: Phase 4 (uses diagnostic)  
**Risk**: MEDIUM — touches control plane, modifies BIS

### Phase 6: CORPUS → CANON Promotion Pipeline
**Goal**: Automated/semi-automated promotion of CORPUS observations to CANON pages.  
**Scope**: LLM-assisted curation: select high-value observations → generate CANON page draft → write to 10_Wiki/ → update index.md + log.md.  
**Files**:
- New: `understanding/curation/promotion.py` (CORPUS → CANON promotion orchestrator)
- New: `understanding/curation/wiki_writer.py` (generates CANON page from observation + template)
- Uses: `canonical_memory_store` as source, `10_Wiki/WIKI_RULES.md` as format contract
- New: tests  
**Dependencies**: Phase 1 (for adapter-sourced observations to promote)  
**Risk**: MEDIUM — writes to 10_Wiki/, must follow WIKI_RULES.md exactly

---

## 9. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Modality as enum, not class hierarchy | Composition over inheritance. An adapter declares modalities, it doesn't inherit from them. |
| D2 | ParticipantType.ECOSYSTEM vs .EXTERNAL | Binary, not graduated. Either you get sockets or you don't. Avoids "semi-ecosystem" complexity. |
| D3 | One canonical pipeline for all adapters | Already exists (GenericIngestionOrchestrator). Don't create a second path. |
| D4 | Maturity separate from health | Maturity = knowledge depth (grows over time). Health = operational state (changes per-second). Different dimensions, different update cadences. |
| D5 | browser-use as CU harness | Python-native, wraps Playwright, MIT, 79k stars, full agent loop. See §5.3. |
| D6 | TME reuse for capability discovery | TME already does: source discovery → doc fetch → content extraction → knowledge write. Same pipeline, different output target. |
| D7 | 10_Wiki + canonical_memory_store = layers, not competitors | CANON pages are curated knowledge. CORPUS entries are machine-generated observations. Adjacent layers in a promotion pipeline. |
| D8 | Notion stays EXTERNAL with socket wiring | No breaking changes. Socket wiring is available to EXTERNAL adapters, just not required. |
| D9 | Shell diagnostic before browser diagnostic | T1 → T2 → T3 ordering. Cheapest/fastest first. Browser is expensive — use last. |
| D10 | Onboarding is re-runnable | `umh diagnostic --full` reruns everything. Idempotent. Updates don't destroy. |

---

## 10. Architecture Questions (All RESOLVED — 2026-05-21)

1. **10_Wiki/codebase/ migration** — RESOLVED at `ebcf068b`.
   Pages moved to gitignored `data/codebase_pages/`. Palace bare-wikilinks resolve via vault root `/opt/OS/`. Bearing principle: retrieval hierarchy treats codebase pages as derivable CORPUS; they violated CANON namespace. Git churn eliminated.

2. **Notion promotion timing** — RESOLVED: no migration.
   Leave socket wiring as-is. Notion stays EXTERNAL (not ECOSYSTEM). Phase 2 adapter framework treats Notion as the reference EXTERNAL case, not the migration target. Socket wiring is legacy/convenience, not architectural. Bearing principle: ParticipantType ECOSYSTEM vs EXTERNAL determines whether socket wiring is architectural or optional.

3. **CU harness LLM integration** — RESOLVED: wire through model_router.
   browser-use wires through `model_router.call_with_fallback()` as a thin adapter. No separate LLM client. Agent loop nests inside model_router's synchronous call pattern via `AgentHarness.run_llm()` threading. Bearing principle: single routing layer = unified token accounting, fallback chain, circuit breaker, CEO escalation. No alternative LLM path exists in the codebase.

4. **SCHEMA layer formalization** — RESOLVED: deferred to Phase 6.
   Current keyword-based BusinessBridge + promotion receipts stay as proto-SCHEMA. 8 domain_projection entries coexist in canonical_memory_store. No Phase 1 work. Bearing principle: CORPUS → CANON → SCHEMA is the 3-layer model; Phase 6 builds the automated promotion pipeline per this architecture doc.

5. **Cross-device diagnostic** — RESOLVED: confirmed Phase 4.
   No active code change. Tailscale transport stays as placeholder in `station_bus.py`. T3 (browser automation) depends on CU harness (Q3). Bearing principle: phased implementation T1 shell → T2 API → T3 browser; cross-device adds network dimension stacked on top.

6. **Memory deduplication** — RESOLVED: trust deterministic hashing.
   No CORPUS-entry promotion marker needed. Deterministic IDs (`mem-{sha256[:16]}` from `candidate_id:source_content_hash`) provide implicit dedup. CORPUS is immutable record; CANON is authoritative form; both persist. Automated promotion pipeline remains Phase 6. Bearing principle: same content = same ID = no re-promotion possible.

---

## 11. Ownership Roadmap

Tracks live external code dependencies only (not absorbed patterns). Each entry documents source, integration state, OST-native wrap interface, migration trigger, and replacement plan.

### 11.1 browser-use (Phase 4 planned)

- **Source**: github.com/browser-use/browser-use (Python, MIT, Playwright wrapper)
- **Integration state**: planned for Phase 4 environmental diagnostic
- **OST-native wrap**: `adapters/adapter_engine/browser_harness.py` exposes CU-modality-generic interface, not browser-use-specific
- **Migration trigger**: internal CU capability available (likely 2027+ depending on compute/training)
- **Replacement plan**: swap implementation behind browser_harness interface; callers unchanged
