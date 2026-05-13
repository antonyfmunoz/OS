# Decomposition Output Audit — 2026-05-12

> READ-ONLY audit. No code changes made.

---

## Decomposer Location + Signature

**Canonical decomposer:** `runtime/ingestion/orchestrator.py:394` — method `GenericIngestionOrchestrator._decompose()`

**Input contract:**
- `signal: Signal` — perception output (signal_id, source_path, content_length)
- `interp: InterpretationResult` — interpretation output (domains, doc_type, intents)
- `raw: RawContent` — original content (content string + sha256)

**Output contract:** `DecompositionResult` from `core/ontology/primitive_decomposition_v1.py`
- **Typed:** YES — Pydantic-style dataclass with enum-typed fields
- Schema: `DecompositionResult.observations: list[PrimitiveObservation]`, `DecompositionResult.relationships: list[PrimitiveRelationship]`
- `PrimitiveObservation` fields: `observation_id, primitive_type: PrimitiveType(Enum), label, description, confidence, source_reference, evidence, is_inferred`
- `PrimitiveRelationship` fields: `from_observation_id, to_observation_id, relationship_type: RelationshipType(Enum), confidence, description`
- Coverage computed via `DecompositionResult.compute_coverage()` — counts by primitive type

**Other decomposition files found (NOT invoked by orchestrator):**
- `runtime/transport/task_decomposition.py` — task pipeline decomposition (builder/product/ceo templates). Unrelated.
- `runtime/substrate/task_decomposition.py` — re-export of the above.

---

## Ontology Primitive Types (core/ontology/primitive_decomposition_v1.py)

```
PrimitiveType: state, change, constraint, resource, signal, action, outcome, feedback, goal, time
RelationshipType: causes, constrains, enables, requires, precedes, follows, produces, consumes, measures, conflicts_with
```

**Important distinction:** These are the *ontology* primitive types used by the ingestion decomposer. They are **completely separate** from `runtime/primitives.py` which defines `KnowledgePrimitive` / `PRIMITIVE_LIBRARY` (business-domain primitives like offer_optimization, hire_salesperson, etc.). The audit prompt asked whether decomposition emits typed primitives like "Stage, Channel, Offer, ICP, Revenue, Role" — those are **business primitives** from `runtime/primitives.py`, not the ontology types from `core/ontology/primitive_decomposition_v1.py`.

The decomposer emits **ontology-level** primitives (state, constraint, resource, etc.), not **business-domain** primitives (Stage, Channel, Offer, ICP, Revenue, Role). These are two different layers.

---

## Three Concrete Proof Samples

### Sample 1 — ingestion_e2e (cloud_palace.md, hand-built)

**File:** `proofs/2026-05-12_ingestion_e2e/03_decomposition.json`
**Source:** `entry_point_invoked.note: "Used contract classes directly. No automated decomposer exists — decomposition is manual using the canonical primitive types."`

This was a **manually constructed** proof that used the `PrimitiveObservation` / `PrimitiveRelationship` contract classes directly. It was NOT produced by `GenericIngestionOrchestrator._decompose()`.

```json
{
  "observations": [
    {"observation_id": "obs-0e040854", "primitive_type": "state", "label": "Memory palace has 4 layers: Palace → Wing → Room → Locus", "description": "The memory palace is structured as a 4-layer navigable hierarchy...", "confidence": 0.95, "source_reference": "cloud_palace.md:lines 30-37", "evidence": "Palace — the whole system...", "is_inferred": false},
    {"observation_id": "obs-0d03b3cf", "primitive_type": "constraint", "label": "AI must translate questions to concerns before navigating rooms", ...},
    {"observation_id": "obs-b06d60d5", "primitive_type": "resource", "label": "Locus rank formula: inbound*2 + outbound + critical*10 + entry*3", ...},
    {"observation_id": "obs-896443fa", "primitive_type": "action", "label": "Navigate palace by concern → room → purpose → core loci", ...},
    {"observation_id": "obs-df208600", "primitive_type": "goal", "label": "Enable AI agents to navigate codebase without blind file scanning", ...},
    {"observation_id": "obs-fe9d56c8", "primitive_type": "signal", "label": "Each room page contains Purpose, Core Loci, Traversal, Raw Paths", ...}
  ],
  "relationships": [4 typed relationships: constrains, enables, produces, requires],
  "decomposition_confidence": 0.88,
  "primitive_type_coverage": {"state": 1, "constraint": 1, "resource": 1, "action": 1, "goal": 1, "signal": 1}
}
```

**Verdict: STRUCTURED** — 6 typed observations across 6 distinct primitive types, 4 typed relationships, semantic labels, evidence trails. This is the gold standard — but it was hand-built, not machine-generated.

### Sample 2 — orchestrator_e2e (runtime_domain_architecture_plan.md, machine-generated)

**File:** `proofs/2026-05-12_orchestrator_e2e/03_decomposition.json`
**Source:** `entry_point_invoked.function: "GenericIngestionOrchestrator._decompose"`

```json
{
  "observations": [
    {"observation_id": "obs-9d1190a4", "primitive_type": "state", "label": "Document has 46 sections", "description": "Structured document with sections: Runtime Domain Architecture Plan, 1. Current State...", "confidence": 0.95},
    {"observation_id": "obs-20b076fc", "primitive_type": "resource", "label": "Domain coverage: architecture", "description": "Document covers the architecture domain based on keyword analysis.", "confidence": 0.95},
    {"observation_id": "obs-5c53725b", "primitive_type": "resource", "label": "Domain coverage: runtime", ...},
    {"observation_id": "obs-54549116", "primitive_type": "resource", "label": "Domain coverage: governance", ...},
    {"observation_id": "obs-645a8610", "primitive_type": "constraint", "label": "### Spine invariants (must hold after stabilization)", "description": "### Spine invariants (must hold after stabilization)", "confidence": 0.85},
    {"observation_id": "obs-014591b7", "primitive_type": "constraint", "label": "Two distinct primitive systems exist and must be preserved:", "description": "Two distinct primitive systems exist and must be preserved:", "confidence": 0.85},
    {"observation_id": "obs-965358f3", "primitive_type": "constraint", "label": "1. **platform/ imports from runtime domains, never the reverse.**", "description": "1. **platform/ imports from runtime domains, never the reverse.**", "confidence": 0.85},
    {"observation_id": "obs-1f79e3da", "primitive_type": "goal", "label": "Document intent: reference_document — structured multi-section content", ...}
  ],
  "relationships": [1 relationship: enables],
  "decomposition_confidence": 0.89,
  "primitive_type_coverage": {"state": 1, "resource": 3, "constraint": 3, "goal": 1}
}
```

**Verdict: PARTIAL** — Typed observations using `PrimitiveType` enum, but:
- **Constraints are raw text lines** (`label` = `description` = the raw markdown line including `###` prefix and `**` formatting). No semantic extraction.
- **Only 1 relationship** for 8 observations (vs 4 for 6 in the hand-built proof). The relationship logic is hardcoded to only create one link between obs[0] and obs[1].
- **"Domain coverage: X"** observations are surface-level keyword hits, not semantic decomposition of what the document says about that domain.
- **Section count** (`"Document has 46 sections"`) is structural metadata, not a business-meaningful primitive.
- No `action`, `signal`, `change`, `outcome`, `feedback`, or `time` types extracted.

### Sample 3 — orchestrator_unification/gws_live (GWS SKILL.md, machine-generated)

**File:** `proofs/2026-05-12_orchestrator_unification/gws_live/03_decomposition.json`
**Source:** `entry_point_invoked.function: "GenericIngestionOrchestrator._decompose"`

```json
{
  "observations": [
    {"observation_id": "obs-31ff2451", "primitive_type": "resource", "label": "Domain coverage: architecture", "description": "Document covers the architecture domain based on keyword analysis.", "confidence": 0.95},
    {"observation_id": "obs-0007fed1", "primitive_type": "resource", "label": "Domain coverage: runtime", ...},
    {"observation_id": "obs-9cd36da5", "primitive_type": "resource", "label": "Domain coverage: governance", ...},
    {"observation_id": "obs-771f64cd", "primitive_type": "constraint", "label": "name: leverage-principle description: Apply the OST leverage principle when reas", "description": "name: leverage-principle description: Apply the OST leverage principle when reasoning about any build, architecture, dependency, sequencing, or strategy decision. Use this skill whenever the user is m", "confidence": 0.85},
    {"observation_id": "obs-eeb127fe", "primitive_type": "constraint", "label": "Never build from zero. Sit above the best existing system, capture the data, int", "description": "Never build from zero. Sit above the best existing system, capture the data, internalize only what becomes load-bearing.", "confidence": 0.85},
    {"observation_id": "obs-7b88a035", "primitive_type": "constraint", "label": "Intelligence lives above the model, not inside it. Infrastructure lives above th", "description": "Intelligence lives above the model, not inside it. Infrastructure lives above the OS, not inside it. Workflow lives above the tool, not inside it. The leverage move is always to wrap, govern, and obse", "confidence": 0.85},
    {"observation_id": "obs-da5882d7", "primitive_type": "goal", "label": "Document intent: protocol_or_policy — contains prescriptive directives", ...}
  ],
  "relationships": [1 relationship: enables],
  "decomposition_confidence": 0.89,
  "primitive_type_coverage": {"resource": 3, "constraint": 3, "goal": 1}
}
```

**Verdict: PARTIAL** — Same pattern as Sample 2:
- Constraints are raw text truncated at 80/200 chars (label/description). The truncation mid-word (`"reas"`, `"int"`, `"obse"`) produces incomplete fragments.
- Domain coverage observations are keyword-hit boilerplate, identical text across documents.
- No heading-count `state` observation because this GWS doc lacked markdown `#` headings (it's Google Docs text content).
- Only 3 of 10 primitive types represented (resource, constraint, goal).

---

## Phase 1 — Aggregate Verdict

| Sample | Source | Generator | Verdict |
|--------|--------|-----------|---------|
| 1 (ingestion_e2e) | cloud_palace.md | Hand-built | **STRUCTURED** |
| 2 (orchestrator_e2e) | runtime_domain_arch_plan.md | `_decompose()` | **PARTIAL** |
| 3 (gws_live) | GWS SKILL.md | `_decompose()` | **PARTIAL** |

**Aggregate verdict: PARTIAL**

The contract types (`DecompositionResult`, `PrimitiveObservation`, `PrimitiveRelationship`) are well-designed and fully typed. The problem is the *decomposer implementation* — `_decompose()` at `orchestrator.py:394-499` uses shallow heuristics:

1. **Section counter** (lines 406-418): Counts `#` headings, emits one `STATE` observation with section names. Structural metadata, not semantic content.

2. **Domain keyword matcher** (lines 420-430): Matches against `_DOMAIN_KEYWORDS` dict. Emits `RESOURCE` observations with boilerplate `"Document covers the {domain} domain based on keyword analysis."` — identical text for every document that mentions "architecture".

3. **Constraint line scanner** (lines 432-445): Grep for `must/never/always/required/forbidden` in lines. Emits raw text as both `label` and `description` with hard truncation at 80/200 chars. No semantic extraction — the markdown formatting (`###`, `**`) is included verbatim. Truncation produces broken fragments.

4. **Intent echo** (lines 447-457): Copies first `intent_candidate` from interpretation stage. Always `"reference_document"` or `"protocol_or_policy"`.

5. **Relationship generator** (lines 471-479): Hardcoded to create exactly one `ENABLES` relationship between obs[0] and obs[1], regardless of document content. No semantic relationship extraction.

### What's missing vs the hand-built proof

| Feature | Hand-built (Sample 1) | Machine-generated (Samples 2-3) |
|---------|----------------------|-------------------------------|
| Semantic labels | Yes — "AI must translate questions to concerns" | No — raw text lines or boilerplate |
| Semantic descriptions | Yes — paraphrased, explained | No — verbatim copy of label or raw text |
| Relationship variety | 4 types (constrains, enables, produces, requires) | 1 hardcoded (enables) |
| Relationship count | 4 for 6 observations | 1 for 7-8 observations |
| Primitive type spread | 6 of 10 types | 3-4 of 10 types |
| Evidence quality | Specific line references, quoted evidence | "keyword overlap" boilerplate or truncated text |
| Missing info / unknowns | Populated | Empty |

### Why this breaks the mastery flywheel

The decomposer produces valid typed containers with shallow content:
- Cannot be queried by semantic meaning (all architecture docs produce identical `"Domain coverage: architecture"` entries)
- Cannot be promoted to named entities (Stage, Channel, Offer, ICP) because the decomposer never identifies them
- Cannot be templated — the content is raw text that needs re-parsing
- Cannot be replayed deterministically for deduplication — label truncation means the same content produces different labels depending on line length
- Relationships are meaningless — always obs[0] ENABLES obs[1] regardless of actual content relationship

---

## Phase 2 — Memory Pollution Check

### Memory entries analysis (13 total in memories.jsonl)

| # | memory_id | primitive_type | label (first 60 chars) | Classification |
|---|-----------|---------------|----------------------|----------------|
| 1 | mem-bf974e9f | resource | "I'd won the money game..." | **TEXT_BLOB** |
| 2 | mem-4bf4f64d | goal | "If you want to see the system I built to escape, click here." | **TEXT_BLOB** |
| 3 | mem-cef137dc | resource | "But because they found the cheat code to unlock the hidden g..." | **TEXT_BLOB** |
| 4 | mem-f9511ef2 | constraint | "Preview: The same programming that got you here is now your..." | **TEXT_BLOB** |
| 5 | mem-2f4f5ca8 | resource | "Body\nHave you ever played a video game and noticed the backg..." | **TEXT_BLOB** |
| 6 | mem-7f088ccd | state | "(First name), there are only two types of people: NPCs..." | **TEXT_BLOB** |
| 7 | mem-53dd62f7 | time | "I spent 2 years building this system after burning out at 22." | **TEXT_BLOB** |
| 8 | mem-81e1243c | time | "I spent 2 years mapping these hidden levels after burning ou..." | **TEXT_BLOB** |
| 9 | mem-54b6aab1 | time | "They walk the same path every day." | **TEXT_BLOB** |
| 10 | mem-0b33152e | time | "Here's what hit me at 22 after cashing in on crypto…" | **TEXT_BLOB** |
| 11 | mem-29c372fa | state | "Memory palace has 4 layers: Palace → Wing → Room → Locus" | **STRUCTURED** |
| 12 | mem-6301934988 | state | "Document has 46 sections" | **PARTIAL** |
| 13 | mem-11bec8e5 | resource | "Domain coverage: architecture" | **PARTIAL** |

### Aggregate memory classification

| Classification | Count | Memory IDs |
|---------------|-------|------------|
| **TEXT_BLOB** | 10 | 1-10 (all from email sequence decomp `decomp-3fb25a245288537b`) |
| **PARTIAL** | 2 | 12, 13 (orchestrator machine-generated) |
| **STRUCTURED** | 1 | 11 (from hand-built ingestion_e2e proof) |

### Analysis

- **Memories 1-10** (decomp `decomp-3fb25a245288537b`): All from the same email sequence document. These are raw sentence extractions with no semantic decomposition. The label IS the content IS the evidence — no abstraction happened. The `primitive_type` assignments are dubious: `"They walk the same path every day."` is classified as `time`, `"I'd won the money game..."` as `resource`. These are marketing copy sentences, not typed entities.

- **No `decomposed_entities` field** exists on any memory entry. Each entry stores the single `best_obs` (highest confidence observation) from the decomposition, not the full decomposition graph. The decomposition-to-memory path is a **lossy funnel**: N observations → 1 persisted memory.

- **No memory can be reverse-mapped** to a typed primitive in `runtime/primitives.py` (the business-domain KnowledgePrimitive library). The decomposer operates on ontology-level types (`state`, `constraint`, `resource`), which have no mapping to business-domain types (`offer_optimization`, `hire_salesperson`, etc.).

---

## Recommendation for Next Phase

### If business-domain primitive extraction is the goal:

The current decomposer operates at the **ontology layer** — it assigns generic types (state, constraint, resource) to text fragments. It does NOT extract business-domain entities (Stage, Channel, Offer, ICP, Revenue, Role) as defined in `runtime/primitives.py`.

These are two separate concerns:
1. **Ontology decomposition** (what exists) — needs deeper semantic extraction to replace shallow heuristics
2. **Business primitive mapping** (what it means for the ventures) — needs a new layer that maps ontology observations to `KnowledgePrimitive` instances

### Recommended next phase: `decomposer-depth-upgrade`

Focus: Replace the 5 shallow heuristics in `_decompose()` with deeper extraction that produces observations at the quality level of the hand-built Sample 1. Specifically:

1. **Semantic labels** — extract the actual claim/fact, not raw text with markdown formatting
2. **Relationship extraction** — analyze observation pairs for semantic relationships instead of hardcoding obs[0]→obs[1]
3. **Broader type coverage** — detect `action`, `change`, `outcome`, `feedback`, `signal`, `time` where present, not just the 3-4 types the keyword scanner finds
4. **Evidence quality** — specific line references instead of `"keyword overlap"` boilerplate
5. **Constraint cleanup** — strip markdown formatting, don't truncate mid-word

This can be done without LLM calls using better text analysis (sentence segmentation, imperative verb detection, entity co-reference). LLM-based decomposition would be a separate phase after this.

### Memory remediation

The 10 TEXT_BLOB entries (memories 1-10) should be re-ingested once the decomposer is upgraded. They currently add noise to retrieval without providing queryable structure.

---

## Open Questions

1. **Is the email sequence decomposer (`decomp-3fb25a245288537b`) a separate path?** Memories 1-10 come from a different decomposition ID not matching any of the three proof bundles. This decomposer may be the `FullLiveIngestionSpine` or an earlier manual run. Its output quality is worse than the orchestrator's.

2. **Is business-domain primitive mapping (Stage/Channel/Offer/ICP) a goal for the ingestion pipeline, or only for the cognitive loop?** The `runtime/primitives.py` library is used by `PrimitiveRegistry` for prompt injection, not by ingestion. If ingestion should also produce business-domain primitives, that's a new requirement beyond fixing the decomposer.

3. **Should the persist stage write all observations or continue writing only `best_obs`?** Current behavior persists a single observation per ingestion cycle. The full decomposition graph is only preserved in proof artifacts, not in `memories.jsonl`.
