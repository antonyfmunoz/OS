---
type: codebase-class
file: eos_ai/substrate/canonical_source_record.py
line: 91
generated: 2026-05-07
---

# DocumentSourceRecord

**File:** [[eos_ai-substrate-canonical_source_record-py]] | **Line:** 91

Canonical record for a fully-extracted document.

## Methods

- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-__post_init__]]`() → None` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-total_tabs]]`() → int` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-total_words]]`() → int` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-total_characters]]`() → int` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-empty_tab_count]]`() → int` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-has_incomplete_tabs]]`() → bool` — 
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-validate_completeness]]`() → tuple[bool, list[str]]` — Validate that this record meets the completeness contract.
- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-to_dict]]`(include_text) → dict[str, Any]` — 

## Decorators

- `@dataclass`
