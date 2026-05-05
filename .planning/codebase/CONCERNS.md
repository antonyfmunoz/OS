# Technical Concerns
*Generated: 2026-03-26*
*Focus: concerns*

## Summary
The EOS codebase is in active development with several documented known issues and technical debt items. The system is currently single-user/single-org, which limits scope of most concerns. The most critical issues are a gateway param mismatch, disabled semantic search, and security risks from host networking and full directory volume mounts.

## Known Issues

| Issue | Location | Severity |
|-------|----------|----------|
| `gateway.py` calls `loop.run(raw_prompt=...)` — param renamed to `input` in Upgrade 3 | `eos_ai/gateway.py` | HIGH |
| Semantic search fully disabled — embedder dimension mismatch (embeddings stored as 384-dim, model outputs different size) | `eos_ai/embedder.py`, `eos_ai/embedding_engine.py` | MEDIUM |
| Discord voice unresolved 4006 bug | `13_Scripts/discord_bot.py` | MEDIUM |

## Technical Debt

| Debt Item | Location | Impact |
|-----------|----------|--------|
| Hardcoded venture IDs in gateway routing | `eos_ai/gateway.py` | Blocks multi-tenant use |
| `VentureKnowledgeBase` is a static Python dict, not DB-driven | `eos_ai/venture_knowledge.py` | Tight coupling, not scalable |
| TODO strings in venture data that reach agent prompts | `eos_ai/venture_knowledge.py` | Degrades agent output quality |
| Ollama URL hardcoded to `localhost` | `eos_ai/agent_runtime.py` | Breaks if Ollama moves |
| `orchestrator.py` is 1,461 lines — monolithic | `eos_ai/orchestrator.py` | Hard to maintain, test, extend |

## Security Concerns

| Concern | Location | Risk Level |
|---------|----------|------------|
| Two containers running `network_mode: host` — bypasses Docker network isolation | `docker-compose.yml` | HIGH |
| Instagram session cookies written to disk | `13_Scripts/dm_monitor.py` | MEDIUM |
| Full `/opt/OS` directory volume-mounted read-write into all containers | `docker-compose.yml` | MEDIUM |

## Incomplete / TODO Items

| Item | Location | Status |
|------|----------|--------|
| Embeddings schema migration not run | `eos_ai/embedding_engine.py` | Blocked |
| Empyrean Creative venture has no real ICP/competitor data | `eos_ai/venture_knowledge.py` | Placeholder |
| WorldPulse AI insight step commented out | `eos_ai/world_pulse.py` | Disabled |

## Scalability Concerns

| Concern | Current State | Threshold |
|---------|---------------|-----------|
| No DB connection pooling | New connection per query via `get_conn()` | Will bottleneck at concurrent requests |
| `qwen2.5:3b` running system-wide — Anthropic credits depleted | All LLM calls via Ollama fallback | Output quality degraded vs Sonnet |
| In-memory venture cache — no TTL or invalidation | Loaded at import time | Stale data after venture edits |

## Key Files

- `eos_ai/gateway.py` — known broken param, do not touch without reading first
- `docker-compose.yml` — host networking security risk
- `eos_ai/orchestrator.py` — 1,461 lines, highest complexity/risk file
- `eos_ai/venture_knowledge.py` — hardcoded data that should be DB-driven
- `eos_ai/embedding_engine.py` — disabled feature with schema migration pending
