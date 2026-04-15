---
type: codebase-function
file: core/tool_mastery_author_agent/loader.py
line: 49
generated: 2026-04-12
---

# sanitize_text

**File:** [[core-tool_mastery_author_agent-loader-py]] | **Line:** 49
**Signature:** `sanitize_text(text) → str`

Remove non-prose noise from a raw HTTP capture.

Strips scripts, styles, Next.js flight payloads, base64/hex blobs, and
JSON-looking lines before returning the residue. The result is NOT a
rendered DOM — it is "HTML minus obvious garbage", still containing
...

## Calls

- [[core-tool_mastery_author_agent-loader-py-_symbol_density]]

## Called By

- [[core-tool_mastery_author_agent-loader-py-_read_text_safely]]
- [[scripts-measure_phase8_batch-py-re_extract_patterns]]
