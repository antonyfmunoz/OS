---
type: codebase-function
file: eos_ai/substrate/extraction_parity_comparator.py
line: 288
generated: 2026-05-07
---

# build_parity_report

**File:** [[eos_ai-substrate-extraction_parity_comparator-py]] | **Line:** 288
**Signature:** `build_parity_report(reference_backend, candidate_backend, reference_records, candidate_records) → dict[str, Any]`

Build a multi-document parity report between two backends.

## Calls

- [[eos_ai-substrate-canonical_source_record-py-DocumentSourceRecord-to_dict]]
- [[eos_ai-substrate-canonical_source_record-py-ProvenanceRecord-to_dict]]
- [[eos_ai-substrate-canonical_source_record-py-TabSourceRecord-to_dict]]
- [[eos_ai-substrate-extraction_backend_contracts-py-BackendCapabilityReport-to_dict]]
- [[eos_ai-substrate-extraction_backend_contracts-py-CanonicalExtractionContract-to_dict]]
- [[eos_ai-substrate-extraction_backend_contracts-py-CapabilityDeclaration-to_dict]]
- [[eos_ai-substrate-extraction_parity_comparator-py-ParityReport-to_dict]]
- [[eos_ai-substrate-extraction_parity_comparator-py-TabParityResult-to_dict]]
- [[eos_ai-substrate-extraction_parity_comparator-py-TextParityResult-to_dict]]
- [[eos_ai-substrate-extraction_parity_comparator-py-compare_document_records]]
