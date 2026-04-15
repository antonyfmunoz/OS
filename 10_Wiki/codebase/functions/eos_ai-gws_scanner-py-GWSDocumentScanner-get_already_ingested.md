---
type: codebase-function
file: eos_ai/gws_scanner.py
line: 149
generated: 2026-04-12
---

# GWSDocumentScanner.get_already_ingested

**File:** [[eos_ai-gws_scanner-py]] | **Line:** 149
**Signature:** `get_already_ingested() → dict`

**Class:** [[eos_ai-gws_scanner-py-GWSDocumentScanner]]

Returns doc_id → modified_time for docs already in Neon.
Queries the events table where KnowledgeIntegrator logs metadata.

## Called By

- [[eos_ai-gws_scanner-py-GWSDocumentScanner-scan_all]]
