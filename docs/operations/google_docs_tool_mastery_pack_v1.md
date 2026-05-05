# Google Docs Tool Mastery Pack — v1

**Phase**: 96.6
**Status**: ACTIVE
**Date**: 2026-05-05

---

## Core Rule

Google Docs has document tabs. First-tab-only extraction is silent data loss. This mastery pack encodes the expert knowledge required to extract Google Docs content completely.

## Master-Level Facts

1. Google Docs can have **document tabs** — a single document may contain multiple content tabs.
2. Tabs can have **child tabs** — nested arbitrarily deep.
3. First-tab-only extraction is a **silent data loss risk** — no error, no warning, just missing content.
4. `documents.get` without `includeTabsContent=true` **silently misses tab content** — returns only the first tab body.
5. Full extraction requires passing `includeTabsContent=true` to the API.
6. Full extraction requires traversing `document.tabs` — iterating all top-level tabs.
7. Full extraction requires **recursively traversing `childTabs`** on each tab.
8. Body text must be **attributed to the correct tab** — not flattened into a single blob.
9. Empty tabs must be **marked as empty**, not silently skipped.
10. **Per-tab provenance** must be preserved — which text came from which tab.
11. **Word counts** per tab and per document must be computed for parity validation.
12. Completeness validation must **detect first-tab-only risk** — flag if only one tab's content was returned when multiple exist.
13. **Parity validation**: doc count, tab count, child tab count, word count, provenance must all match expectations.
14. UI/CU extraction must also **discover and navigate tabs** — screen-based extraction is not exempt.
15. Export/archive must **prove tab preservation** — exported content must include all tabs.

## Anti-Patterns (8)

1. **Reading only `document.body`** — misses all tabs except the first.
2. **Assuming one document = one content body** — documents can have many tabs.
3. **Ignoring tabs entirely** — treating the API response as if tabs don't exist.
4. **Flattening tabs without provenance** — combining all text without tracking which tab it came from.
5. **Treating empty tabs as extraction failures** — an empty tab is valid, not an error.
6. **Marking extraction complete without tab count validation** — "got some text" is not "got all text."
7. **Treating API success as coverage success** — a 200 response does not mean all content was returned.
8. **Treating CLI/MCP success as complete without proving all-tabs support** — wrappers may not pass `includeTabsContent=true`.

## Validation Checklist (11)

1. `includeTabsContent=true` is set in the API call.
2. Top-level tabs are counted and recorded.
3. Child tabs are counted recursively.
4. Per-tab text is extracted and stored separately.
5. Empty tabs are marked as empty (not skipped).
6. Inaccessible tabs are marked as inaccessible (not silently dropped).
7. Per-tab provenance is preserved in the output record.
8. Total word count is computed (per-tab and aggregate).
9. First-tab-only risk is checked — if multiple tabs exist, verify all were extracted.
10. Canonical source record is emitted with full tab metadata.
11. Parity comparator passes — doc count, tab count, child tab count, word count, provenance all match.

## Failure Modes

| Mode | Symptom | Cause | Remediation |
|------|---------|-------|-------------|
| Silent tab loss | Extraction returns text but fewer tabs than expected | `includeTabsContent` not set | Add `includeTabsContent=true` to API call |
| Child tab loss | Top-level tabs present but child tabs missing | Non-recursive traversal | Implement recursive `childTabs` traversal |
| Provenance loss | All text present but tab attribution missing | Flattened extraction | Attribute text to source tab before storage |
| False completeness | Extraction marked complete with partial data | No tab count validation | Add tab count check to completeness gate |

## Completeness Requirements

- Every tab in `document.tabs` must have a corresponding extraction record.
- Every child tab must be recursively discovered and extracted.
- Word count per tab must be non-zero unless the tab is explicitly empty.
- Total extracted word count must match the sum of all per-tab word counts.
- Parity comparator must pass before extraction is marked complete.

## References

- `docs/operations/google_docs_all_tabs_extraction_contract_v1.md` — extraction contract
- `docs/operations/tool_mastery_pack_doctrine_v1.md` — mastery pack requirements
- `docs/operations/google_workspace_backend_options_matrix_v1.md` — access path matrix
- `eos_ai/adapter_engine_contracts.py` — ToolMasteryPack dataclass
