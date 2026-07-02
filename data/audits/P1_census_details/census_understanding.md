# P1 Phase 1A — Capability Census: understanding/, intelligence/, memory/

**Total modules**: 65 (54 understanding + 4 intelligence + 7 memory)
**Excluding**: `__init__.py` files (11), leaving 54 substantive modules

---

## substrate/understanding/ (38 substantive modules)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|------------|
| `breadth_expansion.py` | understanding | DORMANT | 1 | Expands narrow inputs to cover adjacent domains/concepts (step 9 of 27-step spine) | No — overlaps with InputIntelligence prompt enhancement |
| `deliberation/council.py` | reasoning | PARTIALLY_INTEGRATED | 2 | 7-role multi-perspective advisory (strategist, skeptic, completeness, risk, domain, engineer, synthesis judge) for high-risk decisions | YES — canonical deliberation system |
| `domains/business.py` | understanding | PARTIALLY_INTEGRATED | 2 | Maps ontology primitives to business domain concepts | YES — canonical business domain bridge |
| `domains/contract.py` | infrastructure | PARTIALLY_INTEGRATED | 6 | Defines DomainBridge protocol and DomainProjection dataclass | YES — canonical domain bridge contract |
| `domains/creator.py` | understanding | PARTIALLY_INTEGRATED | 3 | Maps ontology primitives to creator domain concepts | YES — canonical creator domain bridge |
| `domains/life.py` | understanding | PARTIALLY_INTEGRATED | 3 | Maps ontology primitives to life domain concepts | YES — canonical life domain bridge |
| `domains/registry.py` | infrastructure | PARTIALLY_INTEGRATED | 2 | Plug-in registry for domain bridges | YES — canonical bridge registry |
| `embedding/embedder.py` | understanding | PARTIALLY_INTEGRATED | 3 | Text→vector embedding (BAAI/bge-small-en-v1.5, 384-dim) | YES — canonical embedder |
| `embedding/embedding_engine.py` | understanding | PARTIALLY_INTEGRATED | 3 | Higher-level embedding operations (batch, similarity search) | YES — canonical embedding engine |
| `intelligence/competitive_intel.py` | understanding | DORMANT | 1 | Competitive intelligence gathering and analysis | No — overlaps with RealityIntelligenceEngine market scanning |
| `intelligence/human_intelligence.py` | understanding | PARTIALLY_INTEGRATED | 5 | HumanIntelligenceEngine — builds profiles of humans the system interacts with (importers: context_builder, event_bus, orchestrator, memory) | YES — canonical human profiling |
| `intelligence/input_intelligence.py` | understanding | PRODUCTION_ACTIVE | 2 | 3-stage input pipeline: ASSESS→ENHANCE→ANNOTATE; elevates vague founder input to world-class execution prompts | YES — canonical input enhancement |
| `intelligence/person_recognition.py` | perception | PRODUCTION_ACTIVE | 8 | Recognizes known people in messages, links to HumanIntelligenceProfile (importers: cognitive_loop, discord_bot_commands, intent_handler, calendly_webhook, scheduling) | YES — canonical person recognition |
| `intelligence/stakeholder_map.py` | understanding | PARTIALLY_INTEGRATED | 2 | Maps stakeholder relationships and influence networks | YES — canonical stakeholder mapping |
| `interpretation/interpretation_engine_v1.py` | understanding | DORMANT | 1 | Multi-stage interpretation with ConfidenceEnvelope and InterpretationBoundary | No — superseded by cognitive_loop's inline interpretation |
| `knowledge/knowledge_domains.py` | understanding | PARTIALLY_INTEGRATED | 3 | KnowledgeDomainRegistry — 21 domains across 8 categories; layers 1-5 domain knowledge | YES — canonical domain knowledge registry |
| `knowledge/knowledge_graph.py` | understanding | PARTIALLY_INTEGRATED | 2 | KnowledgeGraph — entity relationships and traversal | YES — canonical knowledge graph |
| `knowledge/knowledge_integrator.py` | learning | PRODUCTION_ACTIVE | 7 | KnowledgeIntegrator — permanently integrates execution outcomes into knowledge base (importers: cognitive_loop, gateway, discord_bot, research_engine, world_pulse) | YES — canonical knowledge integration |
| `knowledge/knowledge_layers.py` | understanding | PRODUCTION_ACTIVE | 1 | KnowledgeLayerEngine — 12 behavioral distillation layers (6-17) with 110 principles, trigger-matched top-2 injection | YES — canonical behavioral knowledge |
| `knowledge/philosophy_lenses.py` | understanding | PRODUCTION_ACTIVE | 1 | LensEngine — codified philosophy lenses from PHILOSOPHY.md Section VII, values-based filtering | YES — canonical philosophy lens injection |
| `ontology/primitive_decomposition_v1.py` | understanding | PARTIALLY_INTEGRATED | 11 | PrimitiveType/RelationshipType/PrimitiveObservation — decomposes knowledge into first-principles primitives | YES — canonical ontological decomposition |
| `ontology/primitives.py` | reasoning | PRODUCTION_ACTIVE | 6 | PrimitiveRegistry + ContextualReasoningEngine — stage-filtered reasoning that filters output by business context | YES — canonical contextual reasoning |
| `patterns/leverage_patterns.py` | understanding | PRODUCTION_ACTIVE | 2 | Detects 5 "leverage killer" behaviors (building-over-selling, etc.) — used by gateway.py | YES — canonical leverage pattern detection |
| `patterns/pattern_engine.py` | understanding | PARTIALLY_INTEGRATED | 3 | PatternEngine — cross-session behavioral pattern detection, trend analysis | YES — canonical pattern engine |
| `perception/orchestrator.py` | perception | PARTIALLY_INTEGRATED | 4 | GenericIngestionOrchestrator — source-agnostic 7-stage pipeline: perceive→interpret→decompose→bridge→map→persist→query | YES — canonical ingestion pipeline |
| `perception/source.py` | perception | PARTIALLY_INTEGRATED | 8 | RawContent + Source abstraction for the ingestion pipeline | YES — canonical source abstraction |
| `perception/parsers/base.py` | perception | DORMANT | 0 | ParsedSymbol/ParsedImport/ParsedFile — shared contracts for language parsers | YES — canonical parser contract |
| `perception/parsers/config_parser.py` | perception | DORMANT | 0 | Top-level key extraction for JSON/YAML/TOML files | YES — canonical config parser |
| `perception/parsers/js_parser.py` | perception | DORMANT | 0 | Regex-based JavaScript symbol + import extraction | YES — canonical JS parser |
| `perception/parsers/python_parser.py` | perception | DORMANT | 0 | AST-based Python symbol extraction | YES — canonical Python parser |
| `perception/parsers/sql_parser.py` | perception | DORMANT | 0 | SQL table/view/reference detection | YES — canonical SQL parser |
| `perception/parsers/ts_parser.py` | perception | DORMANT | 0 | TypeScript interface/type extraction (extends JS parser) | YES — canonical TS parser |
| `reality/reality_context.py` | world-model | PARTIALLY_INTEGRATED | 2 | RealityContext — wraps RealityIntelligenceEngine for context injection | No — thin wrapper over reality_engine |
| `reality/reality_engine.py` | world-model | PARTIALLY_INTEGRATED | 3 | RealityIntelligenceEngine — continuous market intelligence: signal scanning, priority tiers (CRITICAL/HIGH/NORMAL/BACKGROUND), truth reports | YES — canonical market intelligence engine |
| `research/research_engine.py` | understanding | PARTIALLY_INTEGRATED | 2 | ResearchEngine — autonomous knowledge gap detection; detects its own gaps, researches from first principles, stores as permanent skills | YES — canonical research engine |
| `signals/founder_capture.py` | perception | PARTIALLY_INTEGRATED | 1 | Detects tasks/ideas/reminders from Discord messages; writes to Neon events for morning brief | YES — canonical founder signal capture |
| `world_model/world_model.py` | world-model | DORMANT | 1 | CanonicalWorldModel + InstanceWorldModel — two-layer domain knowledge (patterns/causal/strategies) with promotion | No — overlaps with reality_model/canonical.py |
| `world_pulse/world_pulse.py` | perception | PARTIALLY_INTEGRATED | 2 | WorldPulse — continuous market/creator intelligence monitoring (daily + weekly scans); compounds via KnowledgeIntegrator | YES — canonical external world monitoring |

---

## substrate/intelligence/ (3 substantive modules)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|------------|
| `runtime.py` | reasoning | PRODUCTION_ACTIVE | 3 | IntelligenceRuntime — 3-layer proprietary non-LLM intelligence: PatternIntelligence (learned patterns), DecisionIntelligence (decision outcomes), PredictiveIntelligence (next-action prediction) | YES — canonical proprietary intelligence |
| `finetune_harness.py` | learning | DORMANT | 0 | LoRA fine-tuning scaffolding for self-hosted models | YES — unique fine-tuning capability (but unused) |
| `training_extractor.py` | learning | DORMANT | 0 | Extracts training data from UMH execution traces for fine-tuning | YES — unique training extraction (but unused) |

---

## substrate/memory/ (6 substantive modules)

| File | Capability | Status | Importers | Unique Contribution | Canonical? |
|------|-----------|--------|-----------|---------------------|------------|
| `auto_reconciler.py` | memory | PARTIALLY_INTEGRATED | 4 | AutoReconciler — bridges promoted memories to canonical store; reconciles gaps between promotion pipeline and permanent storage | YES — canonical memory reconciliation |
| `candidate_generator.py` | memory | PARTIALLY_INTEGRATED | 7 | MemoryCandidateGenerator — stages memory candidates from completed execution traces with deterministic IDs and promotion status tracking | YES — canonical memory candidate generation |
| `canonical_write.py` | memory | PARTIALLY_INTEGRATED | 2 | CanonicalWritePath — single facade for organism-loop memory writes to canonical store | No — thin facade; organism_loop (its main consumer) is itself orphaned |
| `claude_bridge.py` | memory | DORMANT | 1 | Syncs Claude Code memory files (~/.claude/memory/) into substrate memory candidate pipeline | YES — unique Claude Code↔substrate memory bridge |
| `promoter.py` | memory | PRODUCTION_ACTIVE | 6 | MemoryPromoter — evaluates candidates for promotion to durable storage; query-back for cognitive loop enrichment | YES — canonical memory promotion + queryback |
| `watcher.py` | memory | PARTIALLY_INTEGRATED | 2 | Filesystem watcher for agent memory directories using watchdog; auto-detects new memory files | No — overlaps with claude_bridge.py (shared parse_frontmatter logic) |

---

## Summary Statistics

| Status | Count | Percentage |
|--------|-------|-----------|
| PRODUCTION_ACTIVE | 10 | 19% |
| PARTIALLY_INTEGRATED | 28 | 53% |
| DORMANT | 15 | 28% |
| OBSOLETE | 0 | 0% |

### PRODUCTION_ACTIVE (10 modules — in cognitive_loop/gateway/discord_bot import chain)
1. `understanding/intelligence/input_intelligence.py` — InputIntelligence (cognitive_loop step 2a)
2. `understanding/intelligence/person_recognition.py` — person recognition (cognitive_loop, discord_bot_commands)
3. `understanding/knowledge/knowledge_integrator.py` — KnowledgeIntegrator (cognitive_loop step 7b, gateway, discord_bot)
4. `understanding/knowledge/knowledge_layers.py` — KnowledgeLayerEngine (cognitive_loop step 2b-ii)
5. `understanding/knowledge/philosophy_lenses.py` — LensEngine (cognitive_loop step 2d)
6. `understanding/ontology/primitives.py` — ContextualReasoningEngine (cognitive_loop step 5)
7. `understanding/patterns/leverage_patterns.py` — leverage killer detection (gateway)
8. `intelligence/runtime.py` — IntelligenceRuntime (cognitive_loop)
9. `memory/promoter.py` — MemoryPromoter (cognitive_loop step 2c)

### Key Findings

1. **Only 10 of 54 modules are production-active** — 81% of the understanding/intelligence/memory layer is not wired into the primary request flow.

2. **Two competing world models in understanding/**:
   - `world_model/world_model.py` (CanonicalWorldModel — domain knowledge, two-layer promotion) — DORMANT, 1 importer
   - `reality/reality_engine.py` (RealityIntelligenceEngine — market intelligence, signal tiers) — PARTIALLY_INTEGRATED, 3 importers
   - Neither overlaps with `organism/world_model.py` (self-model) or `reality_model/canonical.py` (validated patterns)

3. **6 parsers are fully DORMANT** (zero importers) — Python/JS/TS/SQL/Config/base parsers for the ingestion pipeline exist but nothing calls them.

4. **memory/watcher.py duplicates claude_bridge.py** — both parse Claude Code memory frontmatter with near-identical code (parse_frontmatter, type/confidence maps). Should merge.

5. **Two learning subsystems disconnect**: cognitive_loop uses `KnowledgeIntegrator.integrate()` for permanent knowledge (step 7b) and `IntelligenceRuntime.learn_from_execution()` for proprietary intelligence (step 7c). Neither feeds into the organism's `OutcomeLearningLoop`. Learning from cognitive processing never reaches governed learning.

6. **Perception pipeline is built but unwired**: `perception/orchestrator.py` (GenericIngestionOrchestrator) defines a 7-stage canonical pipeline, and 6 language parsers exist. But nothing in the production flow calls them. The cognitive loop's "PERCEIVE" step uses inline logic, not this pipeline.

7. **DeliberationCouncil is valuable but disconnected**: 7-role advisory system with deterministic-first reasoning. Only 2 importers (advisor, work_packet_engine) — not in the cognitive loop's planning/decision path.

8. **ResearchEngine and WorldPulse are scheduled but not governed**: Both run on cron schedules and integrate via KnowledgeIntegrator, but neither goes through governed mutation or EventSpine.
