---
type: palace-room
room_id: memory_persistence
wing: eos_ai
generated: 2026-04-11
---

# Room — Memory & Persistence

**Wing:** [[eos_ai-wing|eos_ai]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Neon-backed memory, session state, authority, context.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[eos_ai-context-py]] | 86 | — |  |
| 2 | [[eos_ai-db-py]] | 60 | `critical` | Neon (PostgreSQL) connection layer for the Python AI layer. |
| 3 | [[eos_ai-memory-py]] | 33 | `critical` | Persistent memory for OS agents — backed by Neon (PostgreSQL). |
| 4 | [[eos_ai-authority_engine-py]] | 8 | — |  |
| 5 | [[eos_ai-knowledge_integrator-py]] | 7 | — | KnowledgeIntegrator — permanent knowledge accumulation layer. |
| 6 | [[eos_ai-system_context-py]] | 1 | — | SystemContext — interface-aware intelligence layer. |
| 7 | [[eos_ai-session_state-py]] | 0 | — |  |

## Traversal

- Back to wing → [[eos_ai-wing|eos_ai wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  eos_ai/context.py
  eos_ai/db.py
  eos_ai/memory.py
  eos_ai/authority_engine.py
  eos_ai/knowledge_integrator.py
  eos_ai/system_context.py
  eos_ai/session_state.py
```
