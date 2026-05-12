# Ingestion Orchestrator v1 — Design

> Date: 2026-05-12
> Status: IMPLEMENTATION
> Module: runtime/ingestion/

---

## 1. Problem

`FullLiveIngestionSpine` (core/runtime/full_live_ingestion_spine_v1.py) is
the only ingestion orchestrator. It is hardwired to Google Workspace:

- Constructor requires `GoogleDriveAdapterV1` and `GoogleDocsAdapterV1`
- Config expects `safe_doc_url_or_id`, `google_account_identity`
- `execute_full_ingestion()` takes `api_raw_content` (pre-fetched from GWS API)

The **contract classes** it invokes are source-agnostic:
- `PrimitiveObservation`, `DecompositionResult` (core/ontology)
- `MemoryScope`, `MemoryScopeAssignment` (runtime/transport)
- `InstanceSourceContext` (runtime/transport)

ingestion-proof-1 confirmed this: a local markdown file traversed the full
pipeline (perceive → interpret → decompose → map → persist → query) using
contracts directly, with no GWS dependency.

**Gap**: No reusable orchestrator exists for non-GWS sources.

## 2. Source Abstraction

Minimum interface via `typing.Protocol`:

```python
class Source(Protocol):
    source_type: str
    source_id: str
    def read(self) -> RawContent: ...
    def metadata(self) -> dict[str, Any]: ...
    def exists(self) -> bool: ...
```

`RawContent`: dataclass with `content: str`, `content_type: str`,
`size_bytes: int`, `sha256: str`.

First implementation: `LocalFileSource` — wraps a `pathlib.Path`,
computes sha256 on read, detects content_type from extension.

Future implementations (separate phases): `GWSSource`, `URLSource`,
`APISource`.

## 3. Orchestrator

`GenericIngestionOrchestrator` sequences contract invocations:

```
source.read() → _perceive → _interpret → _decompose → _map → _persist → _query_back
```

Each stage:
- Takes the prior stage's output as input
- Invokes existing contract classes (never raw-constructs data)
- Measures wall-clock time
- Returns a typed result dataclass

If any stage raises: catch, populate `IngestionResult` with partial
fields, set `verdict = "FAILED_AT_<stage>"`, include exception trace.
Exceptions never escape `ingest()`.

Dependencies injected via constructor:
- `memory_store_path: Path` — where memories.jsonl lives
- `proof_dir: Path | None` — where to write proof artifacts (optional)

No global state. No singletons. No LLM calls.

## 4. Why Two Artifacts

**Source** owns: "how do I get bytes from this origin?"
**Orchestrator** owns: "given bytes, run the canonical pipeline."

Separating them means:
- Adding a new source (GWS, URL, API) never touches the orchestrator
- Testing the orchestrator doesn't require any external service
- The orchestrator's contract is the same regardless of source type

## 5. Untouched Modules

These existing modules are READ-ONLY in this phase:
- `core/runtime/full_live_ingestion_spine_v1.py` — GWS spine, unmodified
- `core/ontology/primitive_decomposition_v1.py` — contract classes only
- `runtime/transport/memory_scope_contracts.py` — scope enums + governance
- `runtime/transport/instance_ingestion_contracts.py` — instance context
- `data/runtime/canonical_memory_store/` — format unchanged

## 6. Test Plan

1. **Unit**: `LocalFileSource` reads a fixture, returns correct shape
2. **Integration**: Orchestrator runs full cycle on fixture, all 8 fields populated
3. **Query-back**: Persisted entry appears at rank 1 in retrieval
4. **Proof**: Re-run on `runtime_domain_architecture_plan.md`, compare
   contract shapes to ingestion-proof-1 outputs field-by-field
