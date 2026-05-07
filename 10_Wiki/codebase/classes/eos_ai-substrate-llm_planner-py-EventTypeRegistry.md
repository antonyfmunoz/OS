---
type: codebase-class
file: eos_ai/substrate/llm_planner.py
line: 176
generated: 2026-05-07
---

# EventTypeRegistry

**File:** [[eos_ai-substrate-llm_planner-py]] | **Line:** 176

Authoritative registry of valid event types for LLM proposals.

Independent from the scheduler subscriber map.  Defines what
the LLM is allowed to propose, not what currently has handlers.

...

## Methods

- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-__init__]]`() → None` — 
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-version]]`() → int` — 
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-schema_hash]]`() → str` — Deterministic hash of all registered schemas.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-register]]`(schema) → None` — Register an event type schema.  Increments version.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-get]]`(event_type) → EventSchema | None` — Look up a schema by event type.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-is_valid_event_type]]`(event_type) → bool` — Check if an event type is registered.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-event_types]]`() → list[str]` — Sorted list of all registered event types.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_event]]`(event_type, payload) → tuple[bool, str]` — Validate an event_type + payload against the registry.
- [[eos_ai-substrate-llm_planner-py-EventTypeRegistry-validate_proposal]]`(proposal, config) → ValidationResult` — Validate every ProposedEvent in a proposal.
