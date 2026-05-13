# Phase 0 — Authority Tier Touchpoint Discovery

> Date: 2026-05-12

## STOP condition checks

### Memory entry format uses strict schema validation?
**NO — CLEAR.** Memory entries are plain JSON dicts appended to
`memories.jsonl` via `json.dumps(memory_entry)`. No schema validator,
no required-key enforcement. Adding `authority_tier` is additive.

### Source protocol has mandatory constructor coupling?
**NO — CLEAR.** `Source` is a `@runtime_checkable` Protocol with
class-level attributes (`source_type: str`, `source_id: str`) and
three methods. Adding `authority_tier: int` as a class-level attribute
with a default value is backward-compatible. Existing sources that
don't declare it will still satisfy the protocol if we keep it optional
or give it a default.

---

## Touchpoints

### 1. Source protocol (`runtime/ingestion/source.py`)

**Current shape:**
```python
@runtime_checkable
class Source(Protocol):
    source_type: str
    source_id: str
    def read(self) -> RawContent: ...
    def metadata(self) -> dict[str, Any]: ...
    def exists(self) -> bool: ...
```

**Proposed change:**
- Add `authority_tier: int` attribute (default T5_DEFAULT = 5)
- Protocol attribute with default — implementors can override or
  accept the default

**Backward compat:** Protocol attributes with defaults don't break
existing implementations. Concrete classes that don't declare
`authority_tier` will fall back to the default. However, for
`runtime_checkable` isinstance checks to pass, the instance must
have the attribute — so we add it with a default in each concrete
class.

### 2. LocalFileSource (`runtime/ingestion/local_file_source.py`)

**Current shape:**
- Constructor: `__init__(self, path: Path | str)`
- Class attribute: `source_type = "local_file"`

**Proposed change:**
- Add `authority_tier` parameter to `__init__` with default T5_DEFAULT
- Store as `self.authority_tier`
- Validate on init via `validate_tier()`

**Backward compat:** Default parameter — all existing callers unchanged.

### 3. GWSSource (`runtime/ingestion/gws_source.py`)

**Current shape:**
- Constructor: `__init__(self, doc_id, scanner, doc_meta=None)`
- Class attribute: `source_type = "google_workspace"`

**Proposed change:**
- Add `authority_tier` parameter to `__init__` with default T5_DEFAULT
- Store as `self.authority_tier`
- Validate on init via `validate_tier()`

**Backward compat:** Default parameter — all existing callers unchanged.

### 4. Signal (`runtime/ingestion/orchestrator.py`)

**Current shape:**
```python
@dataclass
class Signal:
    signal_id: str
    source_path: str
    source_type: str
    content_sha256: str
    content_length: dict[str, int]
    timestamp_utc: str
    perceive_duration_ms: float
```

**Proposed change:**
- Add `authority_tier: int = 5` field
- `to_dict()` includes it
- `_perceive()` reads `source.authority_tier` and sets it

**Backward compat:** Default field value — existing Signal construction
(only in orchestrator) is updated in the same commit.

### 5. InterpretationResult (`runtime/ingestion/orchestrator.py`)

**Current shape:** 7 fields, no authority_tier.

**Proposed change:**
- Add `authority_tier: int = 5` field
- `to_dict()` includes it
- `_interpret()` copies from Signal

**Backward compat:** Default field — same as Signal.

### 6. DecompositionResult / PrimitiveObservation

**Current shape:** `PrimitiveObservation` in
`core/ontology/primitive_decomposition_v1.py` has no authority_tier.

**Proposed change:** Add `authority_tier: int = 5` to
`PrimitiveObservation`. Each observation inherits from Interpretation.
`_decompose()` and `_decompose_heuristic()` set it.

**Backward compat:** Default field. All existing PrimitiveObservation
construction sites updated in same commit.

### 7. DomainProjection (`runtime/domain_bridge/contract.py`)

**Current shape:**
```python
@dataclass
class DomainProjection:
    projection_id: str
    domain_id: str
    domain_primitive_type: str
    label: str
    description: str
    properties: dict[str, Any]
    ontology_observation_ref: str
    confidence: float
    evidence: str
```

**Proposed change:**
- Add `authority_tier: int = 5` field
- `to_dict()` includes it
- BusinessBridge.bridge() copies from observation

**Backward compat:** Default field. Bridge implementations updated.

### 8. Memory entry serialization (`_persist()`)

**Current shape:** `memory_entry` dict built inline, written as JSON.
No authority_tier key.

**Proposed change:**
- Add `"authority_tier": obs.authority_tier` to canonical entries
- Add `"authority_tier": proj.authority_tier` to projection entries

**Backward compat:** Additive key in JSON dict. No reader rejects it.

### 9. Query-back (`_query_back()`)

**Current shape:** Reads all memories, scores by term overlap, returns
top 5 with rank.

**Proposed change:**
- Include `authority_tier` in retrieved entry dicts
- Default to T5_DEFAULT when field absent (legacy entries)
- NO scoring change in V1

**Backward compat:** Additive field in output. No behavior change.

### 10. Proof artifacts (`_write_proofs()`)

**Current shape:** Writes JSON files for each stage.

**Proposed change:** No explicit change needed — tier flows through
existing `to_dict()` calls. Will appear in proof output automatically
once dataclasses include it.

---

## Summary

10 touchpoints identified. All changes are additive (new field with
default). No STOP conditions triggered. No schema validation to break.
No mandatory constructor coupling to violate.

Propagation chain:
```
Source.authority_tier
  → Signal.authority_tier        (_perceive)
  → Interpretation.authority_tier (_interpret)
  → PrimitiveObservation.authority_tier (_decompose)
  → DomainProjection.authority_tier   (_bridge / BusinessBridge)
  → memory_entry["authority_tier"]    (_persist)
  → retrieved_entry["authority_tier"] (_query_back)
```
