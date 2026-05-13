# Phase 0 Discovery — Decomposer Depth Upgrade

> Date: 2026-05-12

## Current decomposition logic

**Type: Heuristic-only.** Zero LLM calls. Zero imports of model_router
or any AI provider in `runtime/ingestion/orchestrator.py`.

The `_decompose()` method at line 394 uses five static heuristics:

1. **Heading counter** (L406-418): Regex for `#`-prefixed lines. Emits
   one `STATE` observation listing section names.
2. **Domain keyword matcher** (L420-430): Cross-references
   `_DOMAIN_KEYWORDS` dict. Emits `RESOURCE` observations with
   boilerplate description.
3. **Constraint line scanner** (L432-445): Grep for
   must/never/always/required/forbidden. Emits raw text as both label
   and description with hard truncation at 80/200 chars.
4. **Intent echo** (L447-457): Copies first `intent_candidate` from
   interpretation stage. Always one of two fixed strings.
5. **Relationship hardcoder** (L471-479): Creates exactly one ENABLES
   relationship between obs[0] and obs[1].

## Hand-built proof origin

The "1 STRUCTURED" sample from the audit
(`proofs/2026-05-12_ingestion_e2e/03_decomposition.json`) was
**hand-authored** — confirmed by `entry_point_invoked.note`:
`"No automated decomposer exists — decomposition is manual using the
canonical primitive types."` No high-quality extraction code path
exists anywhere in the codebase.

## Other decomposition files (not relevant)

- `runtime/transport/task_decomposition.py` — task pipeline
  decomposition (builder/product/ceo templates). Different domain.
- `runtime/substrate/task_decomposition.py` — re-export of above.

## Upgrade scope verdict

**Approach B: Heuristic → LLM introduction.**

The typed containers (`DecompositionResult`, `PrimitiveObservation`,
`PrimitiveRelationship` in `core/ontology/primitive_decomposition_v1.py`)
are well-designed and do not need modification. The problem is purely
in the extraction logic that populates them.

Plan:
- Add an LLM extraction call using `runtime.model_router` (Gemini 2.5
  Flash primary, Ollama fallback)
- Structured JSON output prompt requesting the target schema
- Parse + validate output against `PrimitiveType` / `RelationshipType`
  enums
- Single retry on validation failure
- Keep existing heuristics as fallback if LLM call fails entirely

## LLM availability

- Gemini 2.5 Flash: API key present (39 chars), primary provider
- Ollama: available as fallback
- Anthropic: credits depleted, not in runtime fallback chain
- CC SDK: available but not appropriate for batch extraction

## Cost estimate

Gemini 2.5 Flash pricing (free tier up to 1M TPM):
- Input: ~2000 tokens per document (avg content + system prompt)
- Output: ~500 tokens (structured JSON)
- Cost: effectively $0 at current volume (< 100 docs/day)

## NOT in scope

- Changing `DecompositionResult` / `PrimitiveObservation` schema
- Persist stage logic (1-of-N funnel)
- Ontology → business primitive bridge
- Re-ingestion of existing memories
