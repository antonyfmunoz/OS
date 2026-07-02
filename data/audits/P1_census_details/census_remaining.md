# P1 Phase 1A — Capability Census: Remaining Substrate Directories

**Directories covered**: composition/ (45), foundation/ (4), integrations/ (5),
meta_ide/ (18), observability/ (5), ontology/ (8), operator/ (19), top-level (4)
**Total**: 108 files

---

## substrate/ (top-level, 4 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | PRODUCTION_ACTIVE | — | Substrate public API — Substrate.execute_intent() |
| canonical_types.py | infrastructure | PRODUCTION_ACTIVE | 2 | Single source of truth for all UMH domain types |
| self_model.py | self-model | PRODUCTION_ACTIVE | 21 | Substrate self-awareness — get_ai_name(), handler prefix |
| types.py | infrastructure | PRODUCTION_ACTIVE | 48 | Core domain types — SignalEnvelope, RiskClass, etc. (highest-imported) |

---

## substrate/composition/ (45 files)

### Core (2 files)
| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| knowledge_gap_trigger.py | learning | PARTIALLY_INTEGRATED | 1 | Detects gaps during execution, triggers composition |

### registries/ (1 file)
| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| canonical_command_registry_v1.py | governance | TRANSITIVE_ACTIVE | 7 | Canonical command definitions for governed routing |

### mastery/authoring/ (12 files) — Tool Mastery Author Agent
| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | learning | — | — | Package init |
| __main__.py | learning | DORMANT | 0 | CLI entry point |
| agent.py | learning | DORMANT | 0 | Author agent orchestrator |
| cli.py | learning | DORMANT | 0 | CLI interface |
| draft.py | learning | DORMANT | 0 | Draft authored section content |
| loader.py | learning | PARTIALLY_INTEGRATED | 2 | Research artifact loader |
| mapping.py | learning | PARTIALLY_INTEGRATED | 2 | Section→evidence mapping |
| models.py | learning | DORMANT | 0 | Data types for author agent |
| paths.py | learning | DORMANT | 0 | Path resolution |
| reconcile.py | learning | DORMANT | 0 | Reconcile drafts with on-disk skills |
| verify.py | learning | DORMANT | 0 | Verify authored tool skills |

### mastery/management/ (10 files) — Tool Mastery Manager
| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | learning | — | — | Package init |
| active_tool_context.py | learning | DORMANT | 0 | Active tool context tracking |
| backlog.py | learning | DORMANT | 0 | Backlog/bootstrap flow |
| coverage.py | learning | DORMANT | 0 | Coverage evaluation |
| discovery.py | learning | DORMANT | 0 | Tool discovery |
| ensure.py | learning | PARTIALLY_INTEGRATED | 1 | Primary entry point — ensure_mastery() |
| maintenance.py | learning | DORMANT | 0 | Maintenance flows |
| mastery_assurance.py | learning | PARTIALLY_INTEGRATED | 2 | Mastery assurance gate |
| models.py | learning | DORMANT | 0 | Data types |
| paths.py | learning | DORMANT | 0 | Path resolution |
| tool_mastery_resolver.py | learning | PARTIALLY_INTEGRATED | 2 | Natural language tool resolver |

### mastery/research/ (18 files) — Tool Mastery Research Agent
| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | perception | — | — | Package init |
| __main__.py | perception | DORMANT | 0 | CLI entry point |
| agent.py | perception | PARTIALLY_INTEGRATED | 1 | Research agent orchestrator |
| artifact.py | perception | DORMANT | 0 | Artifact writer |
| candidate_approval.py | perception | DORMANT | 0 | Candidate approval gate |
| cli.py | perception | PARTIALLY_INTEGRATED | 1 | CLI interface |
| docs_site_discovery.py | perception | DORMANT | 0 | Docs site discovery |
| extraction.py | perception | PARTIALLY_INTEGRATED | 1 | Structured knowledge extraction |
| fetcher.py | perception | DORMANT | 0 | Web fetcher |
| github_extractor.py | perception | DORMANT | 0 | GitHub repo extraction |
| handoff.py | perception | DORMANT | 0 | Safe metadata handoff |
| headless_fetcher.py | perception | DORMANT | 0 | Headless browser fetcher |
| models.py | perception | PARTIALLY_INTEGRATED | 1 | Data types |
| paths.py | perception | DORMANT | 0 | Path resolution |
| search_discovery.py | perception | DORMANT | 0 | Deterministic search candidates |
| source_discovery.py | perception | PARTIALLY_INTEGRATED | 1 | Source discovery |
| source_quality.py | perception | DORMANT | 0 | Source quality scoring |
| structured_crawl.py | perception | DORMANT | 0 | Structured crawl expansion |

**TME Summary**: 40 files total. The Tool Mastery Engine is a self-contained subsystem with research→author→management pipeline. Most files are DORMANT (26/40) because the pipeline is not wired into daemon or cognitive loop entry points. Core capability: autonomous tool skill acquisition from web research. Unique and valuable — should be wired as a governed capability, not deleted.

---

## substrate/foundation/ (4 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| identity.py | self-model | PARTIALLY_INTEGRATED | 2 | Identity continuity schema — coherent self across context switches |
| laws.py | governance | TRANSITIVE_ACTIVE | 3 | Substrate laws — re-exports from ontology.laws |
| perspective.py | understanding | PARTIALLY_INTEGRATED | 1 | Perspective schema — interpretive lens for signals |

---

## substrate/integrations/ (5 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| bridge.py | infrastructure | DORMANT | 0 | UMH Bridge to model_router — unused |
| cors.py | infrastructure | PARTIALLY_INTEGRATED | 1 | CORS configuration |
| health.py | infrastructure | DORMANT | 0 | Health aggregator dashboard |
| product_connections.py | infrastructure | PARTIALLY_INTEGRATED | 1 | SaaS product connection manager (EOS, CreatorOS, LYFEOS) — PROJECTION LEAK if not role-based |

**Note**: product_connections.py names specific projections. Should use projection registry pattern.

---

## substrate/meta_ide/ (18 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | execution | — | — | Package init |
| browser_evidence_collector.py | governance | PARTIALLY_INTEGRATED | 1 | Browser verification evidence — executor nodes |
| browser_verification_gate.py | governance | PARTIALLY_INTEGRATED | 3 | Blocking validation gate for UI work |
| engineering_execution.py | execution | PARTIALLY_INTEGRATED | 5 | Governed engineering session types |
| engineering_intent.py | planning | PARTIALLY_INTEGRATED | 5 | Autonomous engineering planning types |
| engineering_planner.py | planning | PARTIALLY_INTEGRATED | 4 | Deterministic planning from high-level intent |
| engineering_session_coordinator.py | coordination | PARTIALLY_INTEGRATED | 3 | Governed execution orchestration |
| engineering_work_generator.py | execution | PARTIALLY_INTEGRATED | 5 | Bridge plans→governed work packets |
| repository_model.py | perception | PARTIALLY_INTEGRATED | 4 | Read-only git awareness |
| review_package_builder.py | reflection | PARTIALLY_INTEGRATED | 5 | Deterministic proof assembly |
| roadmap_gap_engine.py | planning | PARTIALLY_INTEGRATED | 3 | Detects gaps, recommends engineering work |
| roadmap_intelligence.py | planning | PARTIALLY_INTEGRATED | 3 | Phase and planning awareness |
| shared_planner.py | planning | PARTIALLY_INTEGRATED | 5 | Shared EngineeringPlanner singleton |
| workspace_intelligence.py | perception | PARTIALLY_INTEGRATED | 4 | Engineering-state awareness |
| workspace_observation.py | perception | PARTIALLY_INTEGRATED | 10 | Live engineering runtime observation (highest-imported here) |
| workspace_registry.py | perception | PARTIALLY_INTEGRATED | 2 | Workspace topology source of truth |
| workspace_runtime_graph.py | world-model | PARTIALLY_INTEGRATED | 4 | Canonical workspace topology models |
| workspace_topology_engine.py | world-model | PARTIALLY_INTEGRATED | 6 | Live workspace topology with health |

**Meta IDE Summary**: Engineering planning and workspace awareness subsystem. 17 modules, all PARTIALLY_INTEGRATED (none imported by daemon or cognitive_loop directly). Contains unique capabilities: engineering planning, workspace observation, review package building, repository awareness. These are engineering-specific cognitive capabilities that should be wirable as governed capabilities.

---

## substrate/observability/ (5 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| error_recorder.py | recovery | PRODUCTION_ACTIVE | 11 | Canonical fix-forever error recorder — YES |
| jsonl_rotation.py | infrastructure | PRODUCTION_ACTIVE | 4 | JSONL rotation utility — YES |
| outcome_classifier.py | learning | PARTIALLY_INTEGRATED | 2 | Execution result classification |
| trace_store.py | reflection | PARTIALLY_INTEGRATED | 2 | Append-only JSONL trace persistence |

---

## substrate/ontology/ (8 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| domains/__init__.py | infrastructure | — | — | Domain bridges package |
| domains/contract.py | understanding | DORMANT | 0 | Re-export from understanding.domains.contract |
| domains/creator.py | understanding | DORMANT | 0 | Re-export from understanding.domains.creator |
| domains/life.py | understanding | DORMANT | 0 | Re-export from understanding.domains.life |
| laws.py | governance | PRODUCTION_ACTIVE | 3 | Governing laws — enacted constraints (physics of UMH) |
| primitives.py | infrastructure | PRODUCTION_ACTIVE | 6 | Ontology primitives — computational physics |
| relationships.py | world-model | DORMANT | 0 | Typed relationship edges between observations |

**Note**: ontology/domains/*.py are pure re-exports from understanding.domains — these are backward-compat shims.

---

## substrate/operator/ (19 files)

| File | Capability | Status | Importers | Unique Contribution |
|------|-----------|--------|-----------|---------------------|
| __init__.py | infrastructure | — | — | Package init |
| continuity_engine.py | perception | PARTIALLY_INTEGRATED | 5 | Operator presence + continuity aggregation |
| device_continuity.py | perception | PARTIALLY_INTEGRATED | 2 | Per-device presence state |
| intent_receipt.py | understanding | PARTIALLY_INTEGRATED | 5 | Canonical audit trail for every interaction |
| intent_router.py | understanding | PARTIALLY_INTEGRATED | 4 | Deterministic-first intent classification |
| intent_runtime.py | understanding | PARTIALLY_INTEGRATED | 4 | Intent preservation for continuity |
| operator_attention_engine.py | planning | PARTIALLY_INTEGRATED | 3 | Deterministic ranked priorities |
| operator_context.py | understanding | TRANSITIVE_ACTIVE | 9 | Operator home surface types |
| operator_context_engine.py | understanding | PARTIALLY_INTEGRATED | 7 | Operator home aggregation facade |
| operator_presence.py | perception | PARTIALLY_INTEGRATED | 6 | Presence and continuity types |
| operator_snapshot_runtime.py | understanding | PARTIALLY_INTEGRATED | 2 | Answers the 5 operator questions |
| presence_timeline.py | perception | PARTIALLY_INTEGRATED | 2 | Presence transition tracking |
| repository_context_resolver.py | understanding | PARTIALLY_INTEGRATED | 2 | Workspace→repo context mapping |
| screen_awareness.py | perception | PARTIALLY_INTEGRATED | 5 | Visual workspace context types |
| screen_context_providers.py | perception | PARTIALLY_INTEGRATED | 2 | Three modes of screen awareness |
| screen_observation_engine.py | perception | PARTIALLY_INTEGRATED | 8 | Node-role-aware screen context aggregation |
| voice_query_engine.py | understanding | PARTIALLY_INTEGRATED | 4 | Context-grounded query resolution |
| workstation_session_runtime.py | execution | PARTIALLY_INTEGRATED | 2 | Operator leave/return with context restore |
| workstation_translator.py | perception | PARTIALLY_INTEGRATED | 2 | Beast payload→canonical ScreenSnapshot |

**Operator Summary**: Unified operator perception and intent layer. 18 modules, mostly PARTIALLY_INTEGRATED. Contains unique capabilities: screen awareness, device continuity, voice queries, operator presence, intent classification. These are the operator-facing perception layer — should be wired into cognitive pipeline's PERCEIVE stage.

---

## Cross-Directory Findings

### Projection Leaks in Substrate
- `substrate/integrations/product_connections.py` — names EOS, CreatorOS, LYFEOS directly

### Backward-Compatibility Shims (can be removed)
- `substrate/ontology/domains/contract.py` — re-export from understanding
- `substrate/ontology/domains/creator.py` — re-export from understanding  
- `substrate/ontology/domains/life.py` — re-export from understanding
- `substrate/foundation/laws.py` — re-export from ontology.laws

### Entirely Self-Contained Subsystems
- **Tool Mastery Engine** (substrate/composition/mastery/) — 40 files, research→author→manage pipeline
- **Meta IDE** (substrate/meta_ide/) — 18 files, engineering planning and workspace observation
- **Operator** (substrate/operator/) — 19 files, operator perception and intent

### Dormant Subsystems Needing Decisions
- TME (26/40 files dormant) — Wire as governed capability? Or extract to projection?
- ontology/domains/ (3 files) — Remove shims?
- integrations/bridge.py, integrations/health.py — Dead code?
