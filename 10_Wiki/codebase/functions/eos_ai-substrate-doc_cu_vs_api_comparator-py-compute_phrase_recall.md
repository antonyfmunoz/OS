---
type: codebase-function
file: eos_ai/substrate/doc_cu_vs_api_comparator.py
line: 76
generated: 2026-05-07
---

# compute_phrase_recall

**File:** [[eos_ai-substrate-doc_cu_vs_api_comparator-py]] | **Line:** 76
**Signature:** `compute_phrase_recall(api_text, cu_text, phrase_length, max_phrases) → tuple[int, int]`

Check how many API phrases appear in CU text.

Returns (found_count, total_checked).

## Calls

- [[eos_ai-substrate-doc_cu_vs_api_comparator-py-extract_unique_phrases]]
- [[eos_ai-substrate-doc_cu_vs_api_comparator-py-normalize_text]]

## Called By

- [[eos_ai-substrate-doc_cu_vs_api_comparator-py-compare_doc_extraction]]
