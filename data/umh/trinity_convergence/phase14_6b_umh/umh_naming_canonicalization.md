# UMH Naming Canonicalization

**Phase:** 14.6B-UMH
**Status:** DRAFT — awaiting operator ratification
**Provenance:** CODE_RESOLVED_CURRENT_TRUTH + OPERATOR_CORRECTION

---

## Canonical Product Name

**Universal Meta Harness**

- Abbreviation: **UMH**
- Package name: `universal-meta-harness` (pyproject.toml, line 6)
- This is the canonical product name per operator correction in Phase 14.6B.

---

## Stale / Non-Canonical Names

| Name | Status | Where Found | Occurrences | Action |
|------|--------|-------------|-------------|--------|
| Universal Mastery Hierarchy | STALE / NON-CANONICAL | README.md, CLAUDE.md, cloud.md, knowledge/palace, substrate/self_model.py | ~30 files | Rename to Universal Meta Harness |
| EntrepreneurOS (as system name) | STALE / PROJECTION NAMING DEBT | PHILOSOPHY.md (entire doc), services/discord_bot.py, 503+ total occurrences | ~503 occurrences | Correct: EntrepreneurOS is a projection, not the system |
| AgentOS | STALE / HISTORICAL | Various data/audit files | ~22 occurrences | Remove/replace with UMH |
| EOS (as system abbreviation) | AMBIGUOUS | docker-compose.yml network, env vars, channel names | Hundreds | Disambiguate: EOS = projection, UMH = system |

---

## Name Resolution Matrix

| Context | Correct Name | Incorrect/Stale Name |
|---------|-------------|---------------------|
| The overall system/substrate | Universal Meta Harness (UMH) | Universal Mastery Hierarchy, EntrepreneurOS, AgentOS |
| The Python package | universal-meta-harness | universal-mastery-hierarchy |
| The business/company projection | EntrepreneurOS (EOS) | (correct as projection name) |
| The creator/content projection | CreatorOS | (correct as projection name) |
| The personal life projection | LyfeOS | (correct as projection name) |
| The private operator interface | Cockpit | (correct) |
| The AI persona | Runtime-configurable via get_ai_name() | Hardcoded "DEX" |

---

## Backward Compatibility Aliases (Existing in Code)

These aliases exist for import compatibility and must be preserved until all consumers are migrated:

| File | Alias | Canonical Name |
|------|-------|---------------|
| substrate/control_plane/runtime/gateway.py:1927 | EntrepreneurOSGateway | Gateway |
| substrate/state/context/context.py:59 | EntrepreneurOSContext | SubstrateContext |
| substrate/control_plane/orchestrator/orchestrator.py:1910 | EntrepreneurOSOrchestrator | Orchestrator |

---

## Environment Variable Naming Debt

| Current Var | Should Be | Files Affected |
|-------------|-----------|---------------|
| EOS_ORG_ID | UMH_ORG_ID (with EOS_ORG_ID fallback) | services/discord_bot.py, transports/api/organism_bridge.py |
| EOS_ROUTER_CLAUDE_CLI_ENABLED | UMH_ROUTER_CLAUDE_CLI_ENABLED | docker-compose.yml, adapters/models/model_router.py |
| EOS_ROUTER_CLAUDE_CLI_TARGET | UMH_ROUTER_CLAUDE_CLI_TARGET | docker-compose.yml, adapters/models/model_router.py |
| EOS_ROUTER_CLAUDE_CLI_SESSION | UMH_ROUTER_CLAUDE_CLI_SESSION | docker-compose.yml, adapters/models/model_router.py |
| EOS_DISCORD_TEXT_TRANSPORT_ENABLED | UMH_DISCORD_TEXT_TRANSPORT_ENABLED | docker-compose.yml |
| EOS_DISCORD_TEXT_REPLY_TTS_ENABLED | UMH_DISCORD_TEXT_REPLY_TTS_ENABLED | docker-compose.yml |
| EOS_DISCORD_TEXT_ALLOWED_* | UMH_DISCORD_TEXT_ALLOWED_* | docker-compose.yml |
| EOS_ROOT | UMH_ROOT | Multiple adapter/transport files |
| EOS_SUBSTRATE_ROUTING | UMH_SUBSTRATE_ROUTING | transports/presence/handlers/intent_handler.py |

---

## Docker/Infrastructure Naming Debt

| Current Name | Should Be | File |
|-------------|-----------|------|
| eos_network | umh_network | docker-compose.yml |

---

## Documentation Naming Debt

| File | Issue |
|------|-------|
| README.md line 1 | "UMH — Universal Mastery Hierarchy" → "UMH — Universal Meta Harness" |
| PHILOSOPHY.md (entire file) | Uses "EntrepreneurOS" as if it were the system name, not a projection |
| CLAUDE.md | References "Universal Mastery Hierarchy" |
| cloud.md | References "Universal Mastery Hierarchy" |
| knowledge/palace/index.md | "EOS Memory Palace" → "UMH Memory Palace" |
| knowledge/index.md | EOS naming throughout |
| knowledge/retrieval_rules.md | "AI agents in EOS" → "AI agents in UMH" |

---

## Rules

1. **Universal Meta Harness** is the canonical full product name.
2. **UMH** is the canonical abbreviation.
3. **Universal Mastery Hierarchy** is classified as stale/non-canonical naming debt.
4. **EntrepreneurOS** is a valid projection name but must not be used as the system name.
5. No artifact in this phase promotes Universal Mastery Hierarchy as the canonical product name.
6. The pyproject.toml package name `universal-meta-harness` is the code truth.
7. Backward compatibility aliases in substrate/ are technical debt, not canonical names.
