# Census: state/, contracts/, governance/, sockets/, reality_model/

**Method**: Production status determined by AST transitive import closure from the 4 canonical entry points (`substrate/organism/daemon.py`, `substrate/control_plane/runtime/cognitive_loop.py`, `substrate/control_plane/runtime/gateway.py`, `services/discord_bot.py`). A module is PRODUCTION_ACTIVE only if it appears in that closure. Importer counts are codebase-wide (substrate/transports/services/adapters/nodes/projections). Counts verified: state=44, contracts=11, governance=13, sockets=17, reality_model=7 — all match team-lead's claimed totals.

---

## substrate/state/ (44 modules)

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| storage/db.py | infrastructure | PRODUCTION_ACTIVE | 74 | Neon/psycopg2 connection layer — the single DB gateway for the Python layer | substrate/state/storage (keep) |
| context/context.py | self-model | PRODUCTION_ACTIVE | 74 | SubstrateContext: org/user/venture identity loaded from env/BIS at runtime | substrate/state/context (keep) |
| memory/memory.py | memory | PRODUCTION_ACTIVE | 49 | Primary persistent agent memory backed by Neon (1039L — near god-file threshold) | substrate/state/memory (keep; watch size) |
| business/business_instance.py | world-model | PRODUCTION_ACTIVE | 18 | Venture-stage business context layer | substrate/state/business (keep) |
| business/venture_knowledge.py | world-model | PRODUCTION_ACTIVE | 9 | Per-venture knowledge accumulation (no docstring) | substrate/state/business (keep) |
| providers/provider_state.py | governance | PRODUCTION_ACTIVE | 7 | Global provider state + backpressure + execution budget | substrate/state/providers (keep) |
| transformation_state_ledger.py | memory | PRODUCTION_ACTIVE | 6 | Ledger of transformation state transitions | substrate/state (keep) |
| config/config_store.py | infrastructure | PRODUCTION_ACTIVE | 5 | Layered JSON-file-backed configuration | substrate/state/config (keep) |
| metrics/founder_rate.py | world-model | PRODUCTION_ACTIVE | 4 | Founder-time valuation framework | substrate/state/metrics (keep) |
| stores/skill_store.py | memory | PRODUCTION_ACTIVE | 4 | Canonical write API for skills table | substrate/state/stores (keep) |
| memory/contracts/canonical_memory_store_v1.py | memory | PRODUCTION_ACTIVE | 4 | Append-only replay-safe canonical memory persistence (imported by cognitive_loop) | substrate/state/memory/contracts (keep) |
| finance/expense_tracker.py | perception | PRODUCTION_ACTIVE | 3 | Receipt processing from Gmail RECEIPTS folder | substrate/state/finance (keep) |
| profiles/user_model.py | world-model | PRODUCTION_ACTIVE | 2 | Learns founder's thinking/communication/decision patterns | substrate/state/profiles (keep) |
| stores/profile_store.py | memory | PRODUCTION_ACTIVE | 3 | Canonical write API for human/user/intelligence profiles | substrate/state/stores (keep) |
| work/work_state.py | perception | PRODUCTION_ACTIVE | 3 | Work-state detection + idle gate + adaptive throttling | substrate/state/work (keep) |
| stores/approval_store.py | governance | PRODUCTION_ACTIVE | 7 | SQL-backed multi-tenant approval API (**docstring says deprecated**) | substrate/state/stores (review — deprecated marker) |
| finance/subscription_tracker.py | world-model | PRODUCTION_ACTIVE | 2 | Registry of active subscriptions | substrate/state/finance (keep) |
| logs/decision_log.py | memory | PRODUCTION_ACTIVE | 2 | Permanent record of important conversational decisions | substrate/state/logs (keep) |
| registries/claude_skill_registry.py | memory | PRODUCTION_ACTIVE | 2 | Tracks .claude/skills files, syncs to Neon | substrate/state/registries (keep) |
| registries/skill_registry.py | memory | PRODUCTION_ACTIVE | 2 | Skill registry (no docstring) — **v1, coexists with v2** | substrate/state/registries (MERGE candidate w/ v2) |
| registries/skill_registry_v2.py | memory | PRODUCTION_ACTIVE | 1 | First-class skill objects w/ trust scoring — **v2, coexists with v1** | substrate/state/registries (MERGE target) |
| preferences/model_preferences.py | reasoning | PRODUCTION_ACTIVE | 2 | Multi-model router w/ business-context awareness + human override | substrate/state/preferences (keep; overlaps adapters/models routing) |
| config/settings_persistence.py | infrastructure | PRODUCTION_ACTIVE | 2 | flock + atomic write for settings domains | substrate/state/config (keep) |
| metrics/okr_tracker.py | world-model | PRODUCTION_ACTIVE | 2 | Objectives/Key Results per venture | substrate/state/metrics (keep) |
| stores/task_store.py | memory | PRODUCTION_ACTIVE | 2 | Canonical write API for tasks table | substrate/state/stores (keep) |
| permissions/os_trinity.py | governance | PRODUCTION_ACTIVE | 1 | OS Trinity harness permission layer | substrate/state/permissions (keep) |
| tenancy/tenant.py | governance | PRODUCTION_ACTIVE | 1 | Formal multi-tenant isolation layer (**named "for EOS" — projection leak risk**) | substrate/state/tenancy (keep; audit EOS naming) |
| lifecycle/stage_manager.py | execution | PRODUCTION_ACTIVE | 1 | Auto-updates Notion/Discord/primitives on stage advance | substrate/state/lifecycle (keep) |
| session/session_state.py | memory | PRODUCTION_ACTIVE | 1 | Session state (no docstring) | substrate/state/session (keep) |
| stores/venture_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for ventures table | substrate/state/stores (keep) |
| stores/goal_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for goals/goal_outcomes | substrate/state/stores (keep) |
| stores/context_compaction_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for context_compactions table | substrate/state/stores (keep) |
| stores/embedding_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for embeddings table | substrate/state/stores (keep) |
| stores/entity_link_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for entity_links table | substrate/state/stores (keep) |
| stores/email_folder_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for email_folders table | substrate/state/stores (keep) |
| stores/permission_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for cross_product_permissions | substrate/state/stores (keep) |
| stores/preference_store.py | memory | PRODUCTION_ACTIVE | 1 | Canonical write API for model_preferences table | substrate/state/stores (keep) |
| memory/contracts/memory_conflict_governance_v1.py | governance | PARTIALLY_INTEGRATED | 1 | Conflict governance for canonical memory — only imported by substrate/memory/auto_reconciler.py (not reached from entry points) | substrate/state/memory/contracts (keep; wire auto_reconciler) |
| memory/contracts/canonical_memory_reconciliation_engine_v1.py | recovery | PARTIALLY_INTEGRATED | 1 | Memory reconciliation engine — only imported by auto_reconciler.py | substrate/state/memory/contracts (keep; wire auto_reconciler) |
| memory/contracts/memory_identity_v1.py | memory | PARTIALLY_INTEGRATED | 2 | Deterministic identity model for canonical memories — imported by conflict/reconciliation only | substrate/state/memory/contracts (keep) |
| stores/entity_store.py | memory | PARTIALLY_INTEGRATED | 1 | Entity-hierarchy persistence — imported by transports/api/cockpit_entity_routes.py only (not entry-point reached) | substrate/state/stores (keep) |
| stores/higgsfield_store.py | memory | PARTIALLY_INTEGRATED | 1 | Canonical write API for higgsfield_jobs — imported by services/higgsfield_webhook.py (separate service, not in core closure) | substrate/state/stores (keep) |
| stores/agent_registry_store.py | memory | DORMANT | 0 | Canonical write API for agents table — nothing imports it (27L stub) | substrate/state/stores (ARCHIVE or wire) |
| memory/contracts/canonical_memory_query_contracts.py | memory | DORMANT | 0 | Query contracts for canonical memory — nothing imports it | substrate/state/memory/contracts (ARCHIVE or wire) |

## substrate/contracts/ (11 modules)

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| agent_types.py | infrastructure | PRODUCTION_ACTIVE | 41 | Canonical agent types (TaskType, ModelProvider) — heavily depended on | substrate/contracts (keep — canonical) |
| agent_runtime_contracts.py | infrastructure | PRODUCTION_ACTIVE | 2 | Substrate-owned interface for LLM execution (port) | substrate/contracts (keep) |
| adapter_contracts.py | infrastructure | PRODUCTION_ACTIVE | 1 | Substrate-owned adapter descriptor interface | substrate/contracts (keep) |
| routing_contracts.py | infrastructure | PARTIALLY_INTEGRATED | 2 | Capability classes + routing types — imported by integrations/bridge + adapters routing, not entry-point reached | substrate/contracts (keep) |
| control_plane_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for control-plane subsystems (24L) — nothing imports it | substrate/contracts (ARCHIVE — see conflict note) |
| execution_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for execution pipeline (13L) — nothing imports it | substrate/contracts (ARCHIVE) |
| governance_protocol.py | infrastructure | DORMANT | 0 | Canonical contract for governance engines (11L) — nothing imports it | substrate/contracts (ARCHIVE) |
| infrastructure_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for storage/projection (17L) — nothing imports it | substrate/contracts (ARCHIVE) |
| integration_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for integration adapters (29L) — nothing imports it | substrate/contracts (ARCHIVE) |
| organism_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for agent-society layer (28L) — nothing imports it | substrate/contracts (ARCHIVE) |
| understanding_protocol.py | infrastructure | DORMANT | 0 | Canonical contracts for domain bridges/sources (11L) — nothing imports it | substrate/contracts (ARCHIVE) |

**Note**: 7 of 11 contract protocols are DORMANT — a formal-contract layer that was defined but never wired in. See Key Conflicts.

## substrate/governance/ (13 modules)

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| risk_classes.py | governance | PRODUCTION_ACTIVE | 25 | Semantic classification of action side-effect types | substrate/governance (keep — canonical) |
| policy/authority_engine.py | governance | PRODUCTION_ACTIVE | 8 | Authority evaluation engine (no docstring) | substrate/governance/policy (keep) |
| policy/authority_tier.py | governance | PRODUCTION_ACTIVE | 7 | Authority tier constants + validation for ingestion sources | substrate/governance/policy (keep) |
| policy_engine.py | governance | PRODUCTION_ACTIVE | 6 | Evaluates risk class + context → governance verdict | substrate/governance (keep) |
| quality/quality_gate.py | governance | PRODUCTION_ACTIVE | 4 | Every output passes the four values (515L) | substrate/governance/quality (keep) |
| accountability/accountability.py | governance | PRODUCTION_ACTIVE | 3 | Holds founder to their word | substrate/governance/accountability (keep) |
| security.py | governance | PRODUCTION_ACTIVE | 3 | Input validation, rate limiting, audit logging | substrate/governance (keep) |
| authority.py | governance | PRODUCTION_ACTIVE | 3 | Authority levels enum (what runs without human) | substrate/governance (keep) |
| policy/execution_authority_engine_v1.py | governance | PRODUCTION_ACTIVE | 3 | Execution authority engine v1 (724L) | substrate/governance/policy (keep; overlaps authority_engine — see conflicts) |
| policy/confidentiality.py | governance | PRODUCTION_ACTIVE | 2 | Sensitive-data confidentiality protocol | substrate/governance/policy (keep) |
| validation/completeness_engine.py | governance | PRODUCTION_ACTIVE | 2 | 13-slot completeness validation for plans/workflows | substrate/governance/validation (keep) |
| principles/principle_engine.py | governance | PRODUCTION_ACTIVE | 1 | Injects quality standards into every AI decision (519L) | substrate/governance/principles (keep) |
| validation/output_validator.py | governance | PRODUCTION_ACTIVE | 1 | EOS applies own principles to own outputs | substrate/governance/validation (keep) |

All 13 governance modules are PRODUCTION_ACTIVE. Note overlapping authority engines (authority.py, policy/authority_engine.py, policy/execution_authority_engine_v1.py, policy/authority_tier.py) — see Key Conflicts.

## substrate/sockets/ (17 modules)

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| protocols.py | infrastructure | PRODUCTION_ACTIVE | 29 | Protocol definitions for integration-side contracts | substrate/sockets (keep) |
| envelopes.py | infrastructure | PRODUCTION_ACTIVE | 20 | Data shapes that cross the socket boundary | substrate/sockets (keep) |
| registry.py | infrastructure | PRODUCTION_ACTIVE | 12 | Central integration registration + generic adapter bridge | substrate/sockets (keep) |
| notification.py | execution | PRODUCTION_ACTIVE | 7 | Outbound notification socket abstraction | substrate/sockets (keep) |
| channel_port.py | infrastructure | PRODUCTION_ACTIVE | 6 | Channel-router abstraction port | substrate/sockets (keep) |
| projection_port.py | infrastructure | PRODUCTION_ACTIVE | 5 | Abstract consumption layer for projections (309L) | substrate/sockets (keep) |
| config_port.py | infrastructure | PRODUCTION_ACTIVE | 5 | Runtime config-access abstraction port | substrate/sockets (keep) |
| signal_socket.py | perception | PRODUCTION_ACTIVE | 4 | Inbound intake for external integrations | substrate/sockets (keep) |
| view_socket.py | infrastructure | PRODUCTION_ACTIVE | 4 | Broadcast pipeline-state frames to observers | substrate/sockets (keep) |
| outcome_socket.py | execution | PRODUCTION_ACTIVE | 4 | Outbound result notifications to integrations | substrate/sockets (keep) |
| notification_engine.py | execution | PRODUCTION_ACTIVE | 3 | Multi-channel notification engine | substrate/sockets (keep) |
| capability_socket.py | execution | PRODUCTION_ACTIVE | 4 | Bidirectional execution for integration capabilities (imported by registry + api/mesh) | substrate/sockets (keep) |
| view/broadcaster.py | infrastructure | PRODUCTION_ACTIVE | 1 | sync→async bridge for ViewFrame delivery | substrate/sockets/view (keep) |
| view/websocket.py | infrastructure | PRODUCTION_ACTIVE | 1 | WebSocket endpoint broadcasting ViewFrames to cockpit | substrate/sockets/view (keep) |
| approval_port.py | governance | DORMANT | 0 | Approval-decision abstraction port — nothing imports it | substrate/sockets (ARCHIVE or wire) |
| sensing_port.py | perception | DORMANT | 0 | Perception-registration abstraction port — nothing imports it | substrate/sockets (ARCHIVE or wire) |
| message_port.py | infrastructure | DORMANT | 0 | Conversation-persistence abstraction port — nothing imports it | substrate/sockets (ARCHIVE or wire) |

## substrate/reality_model/ (7 modules)

| Module | Capability | Status | Importers | Unique Contribution | Canonical Owner |
|--------|-----------|--------|-----------|-------------------|----------------|
| reality_intelligence.py | world-model | PRODUCTION_ACTIVE | — | Read-only retrieval + explanation over reality model (678L) | substrate/reality_model (keep) |
| canonical.py | world-model | PRODUCTION_ACTIVE | — | Compressed, reusable canonical intelligence | substrate/reality_model (keep) |
| instance.py | world-model | PRODUCTION_ACTIVE | — | Live operational truth of one user/company/environment | substrate/reality_model (keep) |
| canonical_reality_write.py | world-model | PRODUCTION_ACTIVE | — | Governed write path for non-execution observations | substrate/reality_model (keep) |
| reality_mutation.py | world-model | PRODUCTION_ACTIVE | — | Governed observation-write contracts | substrate/reality_model (keep) |
| reality_query.py | world-model | PRODUCTION_ACTIVE | — | Types for reality interrogation | substrate/reality_model (keep) |
| simulation.py | prediction | PRODUCTION_ACTIVE | — | Non-mutating hypothesis testing / what-if | substrate/reality_model (keep) |

All 7 reality_model modules are PRODUCTION_ACTIVE (transitively reached from entry points).

---

## Convergence Recommendations

### MERGE
- **skill_registry.py + skill_registry_v2.py** — v1 (254L, no docstring) and v2 (478L, first-class objects + trust scoring) coexist, both PRODUCTION_ACTIVE with importers. Migrate v1 callers to v2, retire v1. Canonical target: `skill_registry_v2.py`.
- **Authority engine cluster** — `governance/authority.py` (levels enum), `policy/authority_engine.py`, `policy/execution_authority_engine_v1.py` (724L), `policy/authority_tier.py` all live and overlapping in scope. Consolidate the two engines (`authority_engine` vs `execution_authority_engine_v1`) into one canonical engine; keep `authority.py`/`authority_tier.py` as the constants layer.
- **model_preferences.py (state/preferences) vs adapters/models routing** — model_preferences describes itself as a "multi-model router," overlapping with `adapters/models/model_router.py`. State layer should hold *preferences*, not routing logic. Move routing to adapters; keep preference persistence in state.

### PROMOTE
- **canonical memory v1 cluster** (`canonical_memory_store_v1`, `_reconciliation_engine_v1`, `memory_conflict_governance_v1`, `memory_identity_v1`, `canonical_memory_query_contracts`) — a coherent append-only/reconciliation memory subsystem. `store_v1` is already wired into `cognitive_loop`; the reconciliation/conflict/identity trio is gated behind `substrate/memory/auto_reconciler.py`, which is NOT reached from any entry point. Promote by wiring `auto_reconciler` into the daemon/loop, or explicitly document it as a scheduled/offline job. Then wire `canonical_memory_query_contracts` (currently DORMANT, 0 importers) into the read path.

### ARCHIVE
- **7 DORMANT contract protocols** (`control_plane_protocol`, `execution_protocol`, `governance_protocol`, `infrastructure_protocol`, `integration_protocol`, `organism_protocol`, `understanding_protocol`) — 0 importers each. Either wire them as the enforced port layer for their subsystems, or archive. As-is they are a phantom contract layer that gives false architectural assurance.
- **3 DORMANT socket ports** (`approval_port`, `sensing_port`, `message_port`) — 0 importers. Peers (`channel_port`, `config_port`, `projection_port`, `capability_socket`) are all wired; these three were defined but never adopted. Wire or archive.
- **agent_registry_store.py** (0 importers, 27L stub) and **canonical_memory_query_contracts.py** (0 importers) — DORMANT. Wire or archive.

### Key Conflicts
1. **Phantom port/contract layer**: `substrate/contracts/` has 7/11 protocols DORMANT and `substrate/sockets/` has 3/17 ports DORMANT. This is the same pattern in two places — abstract contracts defined for architectural completeness but never enforced. Decision needed: is the port layer aspirational or load-bearing? If load-bearing, wire subsystems through them; if not, archive to stop them implying a boundary that doesn't exist.
2. **Two authority engines**: `policy/authority_engine.py` and `policy/execution_authority_engine_v1.py` (724L) both PRODUCTION_ACTIVE. The `_v1` suffix implies versioning intent but both are live — a reconvergence risk. Pick one canonical execution-authority owner.
3. **Two skill registries** (v1/v2) both live — canonical-type-divergence risk per Type Coherence Law.
4. **Deprecated-but-active**: `stores/approval_store.py` docstring says "(deprecated)" yet has 7 importers and is PRODUCTION_ACTIVE. Either it's not actually deprecated (fix docstring) or callers need migration off it.
5. **Projection-naming leaks in substrate**: `tenancy/tenant.py` ("for EOS"), `validation/output_validator.py` ("EOS applies its own principles") reference the EOS projection by name inside substrate/ — violates Projection Boundary Law. Audit for hardcoded projection identifiers.
6. **Near-god-file**: `memory/memory.py` at 1039L is the largest module in this census and trending toward the 3000L cap; the canonical memory v1 cluster may be the intended replacement/decomposition — confirm the migration story.
