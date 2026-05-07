---
type: codebase-function
file: services/icp_scorer.py
line: 266
generated: 2026-05-07
---

# score_comment

**File:** [[services-icp_scorer-py]] | **Line:** 266
**Signature:** `score_comment(runtime, comment_text, api_call_counter)`

Score a comment using the sales.icp_qualifier sub-agent.
Returns (result dict or None, input_tokens, output_tokens).

## Calls

- [[services-icp_scorer-py-RateLimiter-wait]]

## Called By

- [[services-icp_scorer-py-main]]
