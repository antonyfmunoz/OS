---
type: palace-room
room_id: intelligence_core
wing: eos_ai
generated: 2026-04-11
---

# Room — Intelligence Core

**Wing:** [[eos_ai-wing|eos_ai]]  
**Palace:** [[../index|EOS Memory Palace]]

## Purpose

Cognition loop, routing, identity, primitives — the mind of EOS.

## Core Loci

Top-ranked files by dependency centrality, criticality, and entry status.
These are the files you most often need; open them before grepping.

| # | Locus | Score | Flags | One-liner |
|---|-------|-------|-------|-----------|
| 1 | [[eos_ai-agent_runtime-py]] | 45 | `critical` | Agent runtime for OS agents. |
| 2 | [[eos_ai-cognitive_loop-py]] | 29 | `critical` | CognitiveLoop — full Perceive → Understand → Plan → Execute |
| 3 | [[eos_ai-model_router-py]] | 15 | `critical` | ModelRouter — standalone multi-model router for EOS. |
| 4 | [[eos_ai-gateway-py]] | 13 | `critical` | EOSGateway — single control plane for all AI operations. |
| 5 | [[eos_ai-primitives-py]] | 11 | `critical` | Primitives — stage-aware business rules and contextual reasoning engine. |
| 6 | [[eos_ai-agent_hierarchy-py]] | 10 | `critical` | Agent hierarchy for EntrepreneurOS. |
| 7 | [[eos_ai-ai_identity-py]] | 10 | `critical` | AIIdentityEngine — foundational AI identity principles. |
| 8 | [[eos_ai-model_preferences-py]] | 4 | — | Multi-model router with business context awareness and full human override. |
| 9 | [[eos_ai-intent_router-py]] | 1 | — | IntentRouter — classify founder messages to the correct agent domain. |

## Traversal

- Back to wing → [[eos_ai-wing|eos_ai wing]]
- Up to palace → [[../index|Memory Palace index]]
- Retrieval rules → [[../../retrieval_rules|retrieval_rules.md]]

## Raw Paths

```
  eos_ai/agent_runtime.py
  eos_ai/cognitive_loop.py
  eos_ai/model_router.py
  eos_ai/gateway.py
  eos_ai/primitives.py
  eos_ai/agent_hierarchy.py
  eos_ai/ai_identity.py
  eos_ai/model_preferences.py
  eos_ai/intent_router.py
```
