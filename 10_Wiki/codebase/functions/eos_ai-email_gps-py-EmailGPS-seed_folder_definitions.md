---
type: codebase-function
file: eos_ai/email_gps.py
line: 95
generated: 2026-04-12
---

# EmailGPS.seed_folder_definitions

**File:** [[eos_ai-email_gps-py]] | **Line:** 95
**Signature:** `seed_folder_definitions() → bool`

**Class:** [[eos_ai-email_gps-py-EmailGPS]]

Seed default GPS folder definitions into Neon on first run.
Safe to run multiple times — uses INSERT ... ON CONFLICT DO NOTHING.
