# Deprecation / Delete-Candidate Plan — Phase 75A

> Generated: 2026-05-02

---

## Overview

No files are deleted in this phase. This document identifies modules that are
redundant, obsolete, or superseded by newer implementations. Each entry includes
the replacement, risk assessment, and conditions for safe removal.

---

## Category 1: runtime_engine Duplicates (42 modules)

These `umh.runtime_engine` modules have newer, cleaner equivalents in
domain-specific packages. The legacy versions were migrated from `eos_ai/`
and may still be referenced by substrate, interfaces, or tests.

### Reasoning Duplicates (11)

| Legacy Module | Replacement | Risk | Safe Removal Condition |
|--------------|-------------|------|----------------------|
| `umh.runtime_engine.causal_attribution` | `umh.reasoning.causal_attribution` | LOW | No remaining imports |
| `umh.runtime_engine.causal_credit` | `umh.reasoning.causal_credit` | LOW | No remaining imports |
| `umh.runtime_engine.causal_memory` | `umh.reasoning.causal_memory` | LOW | No remaining imports |
| `umh.runtime_engine.context_engine` | `umh.reasoning.context_engine` | MEDIUM | Verify session_runtime references |
| `umh.runtime_engine.control_layer` | `umh.reasoning.control_layer` | LOW | No remaining imports |
| `umh.runtime_engine.convergence` | `umh.reasoning.convergence` | LOW | No remaining imports |
| `umh.runtime_engine.counterfactual_eval` | `umh.reasoning.counterfactual_eval` | LOW | No remaining imports |
| `umh.runtime_engine.credit_assignment` | `umh.reasoning.credit_assignment` | LOW | No remaining imports |
| `umh.runtime_engine.influence_orchestrator` | `umh.reasoning.influence_orchestrator` | LOW | No remaining imports |
| `umh.runtime_engine.influence_scoring` | `umh.reasoning.influence_scoring` | LOW | No remaining imports |
| `umh.runtime_engine.meta_weight_engine` | `umh.reasoning.meta_weight_engine` | LOW | No remaining imports |

### Analytics Duplicates (7)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.adaptive_exploration` | `umh.analytics.adaptive_exploration` | LOW |
| `umh.runtime_engine.exploration_engine` | `umh.analytics.exploration_engine` | LOW |
| `umh.runtime_engine.fabric_analytics` | `umh.analytics.fabric_analytics` | LOW |
| `umh.runtime_engine.pattern_engine` | `umh.analytics.pattern_engine` | LOW |
| `umh.runtime_engine.score_distribution` | `umh.analytics.score_distribution` | LOW |
| `umh.runtime_engine.signal_orchestrator` | `umh.analytics.signal_orchestrator` | LOW |
| `umh.runtime_engine.strategy_pattern_memory` | `umh.analytics.strategy_pattern_memory` | LOW |

### Planning Duplicates (3)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.directive_engine` | `umh.planning.directive_engine` | LOW |
| `umh.runtime_engine.hierarchical_planning` | `umh.planning.hierarchical_planning` | LOW |
| `umh.runtime_engine.plan_mutation` | `umh.planning.plan_mutation` | LOW |

### Feedback Duplicates (2)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.outcome_evaluator` | `umh.feedback.outcome_evaluator` | LOW |
| `umh.runtime_engine.outcome_feedback` | `umh.feedback.outcome_feedback` | LOW |

### Policy Duplicates (2)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.foresight_engine` | `umh.policy.foresight_engine` | LOW |
| `umh.runtime_engine.stability_guard` | `umh.policy.stability_guard` | LOW |

### Execution Duplicates (3)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.system_graph` | `umh.execution.system_graph` | LOW |
| `umh.runtime_engine.system_registry` | `umh.execution.system_registry` | LOW |
| `umh.runtime_engine.system_selector` | `umh.execution.system_selector` | LOW |

### Other Duplicates (14)

| Legacy Module | Replacement | Risk |
|--------------|-------------|------|
| `umh.runtime_engine.gateway` | `umh.gateway.entry` | MEDIUM |
| `umh.runtime_engine.meta_goal` | `umh.goals.meta_goal` | LOW |
| `umh.runtime_engine.event_bus` | `umh.signal.event_bus` | MEDIUM |
| `umh.runtime_engine.model_router` | `umh.adapters.model_router` | MEDIUM |
| `umh.runtime_engine.memory` | `umh.memory.storage` | MEDIUM |
| `umh.runtime_engine.memory_fabric` | `umh.persistence_layer.memory_fabric` | LOW |
| `umh.runtime_engine.persistence` | `umh.persistence_layer.persistence` | LOW |
| `umh.runtime_engine.strategy_mutation` | `umh.analytics.strategy_mutation` | LOW |
| `umh.runtime_engine.meta_control` | `umh.reasoning.meta_control` | LOW |
| `umh.runtime_engine.meta_generalization` | `umh.reasoning.meta_generalization` | LOW |
| `umh.runtime_engine.primitives` | `umh.primitives.ontological` | LOW |
| `umh.runtime_engine.calibration` | `umh.reasoning.calibration` | LOW |
| `umh.runtime_engine.objective_arbitration` | `umh.objectives.arbitration` | LOW |
| `umh.runtime_engine.execution_router` | `umh.substrate.execution_router` | LOW |

---

## Category 2: Package-Level Redundancy

### capabilities vs capability
- `umh.capabilities/` (2 files: `__init__.py`, `spec.py`)
- `umh.capability/` (3 files: `__init__.py`, `registry.py`, `router.py`)
- **Assessment**: Different concerns (spec vs registry). Not true duplicates.
- **Action**: Consider merging `capabilities.spec` into `capability` package.

### goals.engine vs goals.goal_engine
- Both exist in `umh/goals/`
- **Assessment**: Likely one is the newer version of the other.
- **Action**: Verify which is imported. Deprecate the unused one.

---

## Category 3: Substrate Overlap with Clean Packages

Some substrate modules duplicate functionality in clean packages:

| Substrate Module | Clean Package Equivalent | Notes |
|-----------------|-------------------------|-------|
| `umh.substrate.execution_router` | `umh.execution.engine` | Substrate has its own routing |
| `umh.substrate.plan_mutation` | `umh.planning.plan_mutation` | Substrate-specific planning |
| `umh.substrate.actions` | `umh.actions` | Substrate action types |

**Action**: These are intentional — substrate wraps clean packages for operator context.
Not delete candidates. Document the relationship.

---

## Removal Protocol

For every delete candidate, follow this sequence:

1. **Grep for imports**: `grep -r "from umh.runtime_engine.<module>" umh/ tests/`
2. **Verify replacement parity**: Read both files, confirm the newer version covers all functionality
3. **Update imports**: Change all import paths to the new module
4. **Run tests**: `pytest tests/ -x -q` — all must pass
5. **Archive**: Move to `umh/_deprecated/` with a README noting the replacement
6. **Remove**: Delete after one release cycle with no regressions

---

## Removal Priority (when Phase 75B is complete)

**Wave 1** (lowest risk — modules with zero external imports):
- All reasoning duplicates (11 modules)
- All analytics duplicates (7 modules)
- Planning duplicates (3 modules)

**Wave 2** (medium risk — verify import chains):
- Feedback duplicates (2)
- Policy duplicates (2)
- Execution duplicates (3)

**Wave 3** (highest risk — core infrastructure duplicates):
- gateway, event_bus, model_router, memory (4)

**Total removable**: ~42 modules (~5.7% of codebase)

---

## Modules NOT Candidates for Removal

The remaining ~105 runtime_engine modules have **no clean equivalent** and contain
valuable EOS-specific logic:

- `cognitive_loop.py` — 8-stage execution wrapper
- `agent_runtime.py` — multi-model LLM dispatch
- `agent_teams.py` — domain sub-agents and team routing
- `ceo_agent.py`, `ceo_intelligence.py` — CEO agent logic
- `knowledge_domains.py`, `knowledge_graph.py` — 21-domain knowledge system
- `skill_registry.py`, `claude_skill_registry.py` — skill management
- `session_runtime.py`, `session_state.py` — session management
- `voice_engine.py`, `voice_interface.py` — voice pipeline
- `portfolio_advisor.py` — board-level advisory
- `reality_engine.py`, `research_engine.py` — market intelligence

These should be preserved and eventually migrated to clean packages as part of
post-MVP evolution.
