---
type: codebase-function
file: eos_ai/person_recognition.py
line: 488
generated: 2026-04-11
---

# score_relationship_health

**File:** [[eos_ai-person_recognition-py]] | **Line:** 488
**Signature:** `score_relationship_health(name, email, ctx) → dict`

Score relationship health for a contact.

Factors: days since last contact, meetings, no-shows, outcomes.
Returns score 0-1 and status label.
