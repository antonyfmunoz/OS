---
type: codebase-class
file: eos_ai/substrate/event_spine.py
line: 96
generated: 2026-05-07
---

# Event

**File:** [[eos_ai-substrate-event_spine-py]] | **Line:** 96

Unified event for the EOS substrate event spine.

Attributes:
    event_id: Globally unique identifier.
    parent_event_id: ID of the parent event (for chunk→reply linkage).
...

## Methods

- [[eos_ai-substrate-event_spine-py-Event-update_status]]`(new_status) → None` — Transition status and update timestamp.
- [[eos_ai-substrate-event_spine-py-Event-serialize]]`() → dict[str, Any]` — Serialize to a JSON-compatible dict.
- [[eos_ai-substrate-event_spine-py-Event-deserialize]]`(data) → 'Event'` — Reconstruct an Event from a serialized dict.

## Decorators

- `@dataclass`
