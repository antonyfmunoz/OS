---
type: codebase-function
file: eos_ai/business_instance.py
line: 315
generated: 2026-04-12
---

# BusinessInstanceManager.create_from_wizard

**File:** [[eos_ai-business_instance-py]] | **Line:** 315
**Signature:** `create_from_wizard(answers) → 'BusinessInstance'`

**Class:** [[eos_ai-business_instance-py-BusinessInstanceManager]]

Create a BusinessInstance from onboarding wizard answers dict.
Uses CognitiveLoop to fill any missing gaps.
Saves to Neon and returns the complete BIS.

## Calls

- [[eos_ai-business_instance-py-BusinessInstanceManager-save_bis]]
