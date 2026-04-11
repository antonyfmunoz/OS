---
type: codebase-class
file: eos_ai/agent_runtime.py
line: 74
generated: 2026-04-11
---

# RateLimiter

**File:** [[eos_ai-agent_runtime-py]] | **Line:** 74

In-memory per-org rate limiter.
Prevents runaway loops or malicious input from draining API credits.
Limits: 10 calls/minute, 200 calls/hour per org.

## Methods

- [[eos_ai-agent_runtime-py-RateLimiter-check]]`(org_id) → bool` — Return True if call is allowed. Return False if rate limited.
