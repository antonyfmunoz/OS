---
type: codebase-function
file: eos_ai/person_recognition.py
line: 71
generated: 2026-04-12
---

# recognize_person

**File:** [[eos_ai-person_recognition-py]] | **Line:** 71
**Signature:** `recognize_person(name, email, ctx) → dict`

Check if a person is known across all memory sources.

Checks in order:
1. Semantic memory search (recent conversations)
2. CRM lead files (03_CRM/Leads/)
...

## Calls

- [[eos_ai-person_recognition-py-create_lead_file]]

## Called By

- [[eos_ai-person_recognition-py-build_intelligence_profile]]
