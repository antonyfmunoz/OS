# FastEmbed — Creator-Level Best Practices
Source: https://github.com/qdrant/fastembed
API Version: N/A (local library, no API versioning)
SDK Version: fastembed 0.8.0
Last Researched: 2026-04-06

---

# Tier 1 — Technical Mastery

## Authentication

N/A — FastEmbed is a local-only library. No API keys, no OAuth, no tokens, no accounts.

Models are downloaded from HuggingFace Hub on first instantiation and cached locally.
The only "auth" scenario: if your HuggingFace Hub is behind a firewall or requires a token
for gated models, set `HF_TOKEN` environment variable. None of the models EOS uses (BGE family)
are gated, so this is not needed.

Cache location: `~/.cache/fastembed/` by default, overridable via `cache_dir` parameter.

## Core Operations with Exact Signatures

### TextEmbedding (primary class)

```python
from fastembed import TextEmbedding

# Constructor
TextEmbedding(
    model_name: str = 'BAAI/bge-small-en-v1.5',  # required — model identifier
    cache_dir: str | None = None,                  # optional — override ~/.cache/fastembed/
    threads: int | None = None,                    # optional — ONNX thread count (default: all cores)
    providers: Sequence[str | tuple] | None = None,# optional — ONNX execution providers
    cuda: bool | Device = Device.AUTO,             # optional — GPU acceleration
    device_ids: list[int] | None = None,           # optional — specific GPU IDs
    lazy_load: bool = False,                       # optional — defer model load to first embed call
    **kwargs: Any
)

# Embed documents (primary method)
TextEmbedding.embed(
    documents: str | Iterable[str],  # single string or iterable of strings
    batch_size: int = 256,           # docs per batch — higher = more memory, faster
    parallel: int | None = None,     # data-parallel workers (None = sequential)
    **kwargs: Any
) -> Iterable[np.ndarray]
# Returns: generator of numpy arrays, each shape (dim,), dtype float32

# Embed queries (adds model-specific prefix like "query: ")
TextEmbedding.query_embed(
    query: str | Iterable[str],  # single query or iterable
    **kwargs: Any
) -> Iterable[np.ndarray]
# Returns: generator of numpy arrays

# Embed passages (alias for embed, may add "passage: " prefix)
TextEmbedding.passage_embed(
    texts: Iterable[str],
    **kwargs: Any
) -> Iterable[np.ndarray]
# Returns: generator of numpy arrays

# List all supported models
TextEmbedding.list_supported_models() -> list[dict]
# Returns: list of dicts with keys: model, dim, description, sources, etc.
```

### SparseTextEmbedding

```python
from fastembed import SparseTextEmbedding

SparseTextEmbedding(
    model_name: str = 'prithvida/Splade_PP_en_v1',
    cache_dir: str | None = None,
    threads: int | None = None,
    providers: Sequence[str | tuple] | None = None,
    **kwargs: Any
)
# Same embed/query_embed interface but returns sparse vectors
```

### ImageEmbedding

```python
from fastembed import ImageEmbedding

ImageEmbedding(
    model_name: str = 'Qdrant/clip-ViT-B-32-vision',
    cache_dir: str | None = None,
    threads: int | None = None,
    **kwargs: Any
)
# embed(images: Iterable[str | Path | Image]) -> Iterable[np.ndarray]
```

## Pagination Patterns

N/A — FastEmbed is not an API with paginated responses. It processes inputs as generators.
For large document sets, use the `batch_size` parameter to control memory:

```python
model = TextEmbedding("BAAI/bge-small-en-v1.5")

# Process 100K documents without loading all into memory
def document_generator():
    for doc in database_cursor:
        yield doc["text"]

# Generator yields one embedding at a time — constant memory
for embedding in model.embed(document_generator(), batch_size=256):
    store_embedding(embedding)
```

The generator pattern means you never need to hold all embeddings in memory simultaneously.

## Rate Limits

N/A — No API rate limits. FastEmbed runs locally. Throughput is bounded by:

- **CPU speed** — ONNX Runtime uses all available cores by default. `threads` parameter controls this.
- **Memory** — Each batch of `batch_size` documents is tokenized and embedded simultaneously.
  256 documents x 512 tokens x float32 = ~500KB per batch for bge-small.
- **Model size in memory** — bge-small: ~150MB, bge-base: ~450MB, bge-large: ~1.3GB resident.

Practical throughput on a 4-core VPS (EOS environment):
- bge-small-en-v1.5: ~500-1000 documents/second for short texts (< 128 tokens)
- bge-base-en-v1.5: ~200-400 documents/second
- bge-large-en-v1.5: ~50-150 documents/second

When running inside Docker, ensure the container has enough memory allocated.
EOS `os-discord` container runs alongside Ollama — monitor with `docker stats`.

## Error Codes and Recovery

FastEmbed raises standard Python exceptions, not HTTP error codes:

| Exception | Cause | Recovery |
|---|---|---|
| `ImportError` | fastembed not installed | `pip install fastembed --break-system-packages` |
| `ValueError` | Invalid model name | Check `TextEmbedding.list_supported_models()` |
| `OSError` / `HTTPError` | Model download failed (no internet, HF Hub down) | Retry, or manually place model in cache_dir |
| `RuntimeError` | ONNX Runtime initialization failed | Check onnxruntime version compatibility |
| `MemoryError` | Model too large for available RAM | Use smaller model or increase container memory |
| `TypeError` | Passing non-string to embed() | Ensure all inputs are strings |

Recovery pattern used in EOS (`embedding_engine.py`):
```python
try:
    model = self._get_text_model()
    embeddings = list(model.embed([text]))
    return embeddings[0].tolist()
except Exception as e:
    print(f'[EmbeddingEngine] fastembed failed: {e} — falling back to Gemini')
    # Falls through to Tier 2
```

All FastEmbed errors are non-retryable in the immediate term (model load failure, OOM).
The correct pattern is to fall back to an alternative, not retry.

## SDK Idioms

### Import pattern
```python
from fastembed import TextEmbedding  # always from fastembed, not fastembed.text
```

### Singleton pattern (EOS standard)
Models are expensive to load (~1-3 seconds). Never instantiate per-request.
```python
# CORRECT: module-level singleton (eos_ai/embedder.py pattern)
_model = None
def _get_model():
    global _model
    if _model is None:
        _model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return _model

# CORRECT: instance attribute with lazy load (eos_ai/embedding_engine.py pattern)
class Engine:
    def __init__(self):
        self._fastembed = None
    def _get_text_model(self):
        if self._fastembed is None:
            self._fastembed = TextEmbedding(self.FASTEMBED_MODEL)
        return self._fastembed
```

### Generator consumption
```python
# CORRECT: consume generator
vec = next(model.embed([text]))           # single document
vecs = list(model.embed(["a", "b"]))      # multiple documents

# WRONG: generator is not subscriptable
vec = model.embed([text])[0]  # TypeError!
```

### Async compatibility
FastEmbed is synchronous. For async contexts (Discord bot), run in executor:
```python
import asyncio
loop = asyncio.get_event_loop()
vec = await loop.run_in_executor(None, lambda: next(model.embed([text])))
```

## Anti-Patterns

### 1. Instantiating model per request
```python
# WRONG — 1-3 second model load on every call
def get_embedding(text):
    model = TextEmbedding("BAAI/bge-small-en-v1.5")
    return next(model.embed([text]))

# CORRECT — singleton, load once
_model = TextEmbedding("BAAI/bge-small-en-v1.5")
def get_embedding(text):
    return next(_model.embed([text]))
```

### 2. Forgetting embed() returns a generator
```python
# WRONG — TypeError: 'generator' object is not subscriptable
result = model.embed(["hello"])[0]

# CORRECT
result = list(model.embed(["hello"]))[0]
# or
result = next(model.embed(["hello"]))
```

### 3. Mixing query_embed and embed for the same use case
```python
# WRONG — asymmetric prefixes cause mismatched similarity scores
doc_vec = next(model.query_embed("document text"))   # adds "query: " prefix
query_vec = next(model.embed(["search query"]))       # no prefix

# CORRECT — use query_embed for queries, embed for documents
doc_vec = next(model.embed(["document text"]))
query_vec = next(model.query_embed("search query"))

# ALSO CORRECT (EOS pattern) — symmetric, both use embed()
doc_vec = next(model.embed(["document text"]))
query_vec = next(model.embed(["search query"]))
```

### 4. Not truncating long inputs
```python
# WRONG — silently truncated at 512 tokens, wasted computation on tokenization
vec = next(model.embed([giant_document]))

# CORRECT — chunk or truncate explicitly
vec = next(model.embed([text[:8000]]))  # EOS guard
# Or better: chunk + average
chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
vecs = list(model.embed(chunks))
avg_vec = np.mean(vecs, axis=0)
```

### 5. Comparing vectors from different models
```python
# WRONG — dimensions and semantic spaces differ
vec_a = next(small_model.embed(["text"]))   # 384-dim
vec_b = next(large_model.embed(["text"]))   # 1024-dim
sim = np.dot(vec_a, vec_b)  # ValueError or meaningless result

# CORRECT — always use the same model for vectors being compared
vec_a = next(model.embed(["text a"]))
vec_b = next(model.embed(["text b"]))
```

### 6. Using parallel > 1 for small batches
```python
# WRONG — parallel overhead exceeds embedding time for small batches
vecs = list(model.embed(["one doc"], parallel=4))

# CORRECT — parallel only for large batches (1000+)
vecs = list(model.embed(large_corpus, batch_size=256, parallel=4))
```

## Data Model

FastEmbed produces numpy arrays, not complex objects:

```
TextEmbedding.embed() → generator of np.ndarray
  - shape: (dim,) where dim depends on model
  - dtype: float32 (default), float16, int8 available for quantized models
  - values: float values, NOT L2-normalized by default
  - BGE models: values typically in [-1.0, 1.0] range

Model info dict (from list_supported_models()):
  {
    "model": "BAAI/bge-small-en-v1.5",   # HuggingFace model ID
    "dim": 384,                            # output vector dimension
    "description": "...",                  # human-readable description
    "sources": {...},                      # download sources
  }
```

EOS storage in Neon:
```sql
CREATE TABLE embeddings (
    id UUID PRIMARY KEY,
    interaction_id UUID REFERENCES interactions(id),
    org_id UUID NOT NULL,
    embedding vector(384),          -- pgvector type, 384-dim for bge-small
    content_preview TEXT,            -- first 200 chars of embedded content
    embedding_model TEXT,            -- 'BAAI/bge-small-en-v1.5' or 'models/gemini-embedding-001'
    created_at TIMESTAMPTZ DEFAULT now()
);
```

## Webhooks and Events

N/A — FastEmbed is a local computation library. No webhooks, no events, no callbacks.

## Limits

| Limit | Value | Notes |
|---|---|---|
| Max input tokens per document | 512 (bge-small/base/large) | Silently truncated, no error |
| Max batch_size | No hard limit | Bounded by available RAM |
| Model download size | 33MB (bge-small), 130MB (bge-base), 650MB (bge-large) | One-time download |
| Resident memory | ~150MB (bge-small), ~450MB (bge-base), ~1.3GB (bge-large) | Per loaded model |
| Output dimensions | Fixed per model (384, 768, or 1024) | Cannot be changed after model selection |
| Concurrent models | Limited by RAM only | Each model is independent in memory |
| Supported languages | English-optimized (BGE); multilingual models available | paraphrase-multilingual-MiniLM-L12-v2 for non-English |

## Cost Model

Free. Zero cost. FastEmbed is Apache 2.0 licensed, runs locally, and uses no paid APIs.

Cost is purely computational:
- **CPU time** — negligible for EOS volumes (< 1000 embeddings/day)
- **RAM** — ~150MB resident for bge-small, permanent while process runs
- **Disk** — ~33MB for cached model files
- **First-run download** — ~33MB from HuggingFace Hub (one-time)

Compared to cloud embedding APIs:
- OpenAI text-embedding-3-small: $0.02 per 1M tokens
- Gemini embedding-001: $0.00 (free tier) to $0.000025 per character
- FastEmbed: $0.00 always

For EOS's volume (hundreds of embeddings/day), cloud APIs would cost < $1/month.
FastEmbed's advantage is zero-latency, zero-dependency, and zero-cost at any scale.

## Version Pinning

**Current SDK version:** fastembed 0.8.0
**Pinned in:** `services/requirements.txt` (unpinned — `fastembed` with no version constraint)
**ONNX Runtime dependency:** onnxruntime (CPU), automatically installed

Recommendation: Pin to `fastembed>=0.8.0,<1.0` in requirements.txt to avoid breaking changes
on major version bumps while getting patch fixes.

FastEmbed follows semver. The 0.x series has had breaking changes between minor versions:
- 0.2 → 0.3: Changed default model from all-MiniLM-L6-v2 to bge-small-en-v1.5
- 0.3 → 0.4: Added SparseTextEmbedding
- 0.4 → 0.5: Added ImageEmbedding
- 0.6+: Added LateInteractionTextEmbedding, Device enum for CUDA

No known upcoming deprecations. The library is actively maintained by Qdrant.

---

# Tier 2 — Creator Intelligence

## Design Intent and Tradeoffs

FastEmbed exists because sentence-transformers (the dominant embedding library) is heavy.
It pulls in PyTorch (~2GB), requires GPU for reasonable speed, and has complex dependency chains.
Qdrant built FastEmbed to solve one problem: make embeddings fast and light for retrieval.

**Design philosophy:**
- ONNX Runtime over PyTorch — 10-50x smaller install, CPU-native performance
- Retrieval-first — optimized for the embed-then-search pattern, not fine-tuning
- Generator-based — constant memory regardless of corpus size
- Model-agnostic — any ONNX model from HuggingFace works

**Conscious tradeoffs:**
- No training/fine-tuning — this is an inference-only library
- No GPU by default — CPU is the first-class citizen (GPU via onnxruntime-gpu)
- No model hosting — models come from HuggingFace, not Qdrant
- Limited to ONNX-exported models — not all HuggingFace models are available

**What FastEmbed is NOT:**
- Not a vector database (that's Qdrant itself)
- Not a training framework (that's sentence-transformers)
- Not a full NLP toolkit (that's spaCy or Hugging Face Transformers)

## Problem-Solution Map and Hidden Capabilities

**Primary problems solved:**
1. Generate embeddings without PyTorch/GPU dependencies
2. Embed large corpora with constant memory (generator pattern)
3. Drop-in replacement for sentence-transformers in retrieval pipelines

**Hidden capabilities:**
- **Sparse + Dense hybrid search** — Combine TextEmbedding (dense) with SparseTextEmbedding
  (SPLADE) for hybrid retrieval. Dense captures semantic meaning, sparse captures exact keywords.
  Qdrant natively supports this combination.
- **Late interaction models** — ColBERT-style token-level matching via LateInteractionTextEmbedding.
  Higher quality than single-vector but ~10x slower. Use for re-ranking, not first-pass retrieval.
- **Multimodal search** — ImageEmbedding + TextEmbedding with compatible CLIP models enables
  text-to-image and image-to-text search.
- **Quantized models** — Some models return int8 or float16 vectors, reducing storage by 2-4x
  with minimal quality loss.
- **Custom ONNX models** — Any ONNX-exported transformer model can be used by placing it in
  the cache directory with the right structure.

## Operational Behavior and Edge Cases

**First-call latency:** Model instantiation takes 1-3 seconds (ONNX session creation).
Subsequent calls are ~1ms per short document. EOS pre-warms at init to avoid this hitting users.

**Thread contention:** ONNX Runtime defaults to using all CPU cores. If multiple processes
load FastEmbed (e.g., Discord bot + a cron script), they compete for CPU. Set `threads=2`
in constrained environments.

**Model cache corruption:** If a download is interrupted, the cached model may be corrupt.
Symptoms: RuntimeError on model load. Fix: delete `~/.cache/fastembed/{model_name}/` and
re-instantiate.

**Empty string handling:** Embedding an empty string returns a valid vector (all near-zero).
This vector will have low similarity to everything, which is correct behavior but can be
surprising. EOS guards with `if not text or not text.strip(): return None`.

**Unicode handling:** FastEmbed's tokenizer handles Unicode correctly. Non-English text
works but produces lower-quality embeddings with English-optimized models. Use multilingual
models (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) for non-English content.

**Determinism:** Same text + same model = same vector. Embeddings are deterministic.
No randomness in inference. Safe to cache and compare across sessions.

## Ecosystem Position and Composition

FastEmbed sits at the **embedding generation layer** in a retrieval architecture:

```
Text Input → [FastEmbed] → Vector → [pgvector / Qdrant] → Search Results
```

**Natural complements:**
- **Qdrant** — Vector database built by the same team. FastEmbed is designed to feed Qdrant.
- **pgvector** — PostgreSQL extension for vector similarity. EOS uses this in Neon.
- **LangChain / LlamaIndex** — Both have FastEmbed integrations as embedding providers.

**EOS composition:**
- FastEmbed generates vectors → stored in Neon pgvector → queried via cosine distance
- Skill matching: FastEmbed vectors → in-memory cosine similarity (no DB needed)
- Interaction memory: FastEmbed vectors → Neon embeddings table → semantic_search()

**What pairs poorly:**
- FastEmbed + sentence-transformers in the same project — redundant, and sentence-transformers
  pulls in PyTorch which defeats the purpose
- FastEmbed + OpenAI embeddings in the same table — different vector spaces, can't compare

## Trajectory and Evolution

FastEmbed is actively maintained by Qdrant (YC-backed, well-funded vector DB company).

**Direction:**
- More models added with each release (30+ as of 0.8.0)
- Sparse embedding (SPLADE) getting first-class support
- Multimodal (image + text) expanding
- Late interaction (ColBERT) recently added
- GPU support improving but CPU remains primary focus

**What to watch:**
- 1.0 release may introduce breaking changes in the API surface
- ONNX Runtime updates occasionally break compatibility — pin onnxruntime version
- New BGE models (bge-m3, bge-en-icl) may become available in FastEmbed

**Safe to build on:** TextEmbedding.embed() and TextEmbedding.query_embed() — these are
the stable core API and unlikely to change. Model names are permanent (HuggingFace IDs).

## Conceptual Model and Solution Recipes

**Mental model:** FastEmbed is a function: `text → vector`. Everything else is configuration.
The vector lives in a metric space where distance = semantic dissimilarity.

**Primitives:**
- `TextEmbedding(model)` — load a model
- `.embed(docs)` — text → dense vector
- `.query_embed(query)` — query text → dense vector (with retrieval prefix)
- `cosine_similarity(a, b)` — compare two vectors

### Recipe 1: Semantic Skill Matching (EOS pattern)
```python
# On startup: embed all skills
from eos_ai.embedder import embed, cosine_similarity
skill_vecs = {name: embed(f"{name}\n{content[:800]}") for name, content in skills.items()}

# On query: find most relevant skill
query_vec = embed(task_description)
scored = [(cosine_similarity(query_vec, sv), name) for name, sv in skill_vecs.items()]
best = sorted(scored, reverse=True)[:3]
```

### Recipe 2: Interaction Memory Search (EOS pattern)
```python
# On every interaction: embed and store
engine = EmbeddingEngine()
engine.embed_interaction(interaction_id, content, org_id)

# On recall: semantic search
results = engine.semantic_search("lead scoring strategy", org_id, limit=5)
# Returns: [{id, agent, task_type, input_summary, output_summary, similarity}]
```

### Recipe 3: Bulk Backfill Missing Embeddings
```python
engine = EmbeddingEngine()
stats = engine.backfill_missing(org_id, limit=200)
# stats: {found: 200, embedded: 185, failed: 5, skipped: 10}
# Rate-limited: 1s pause every 20 rows
```

### Recipe 4: Document Deduplication
```python
model = TextEmbedding("BAAI/bge-small-en-v1.5")
docs = ["first document", "first doc slightly edited", "completely different"]
vecs = list(model.embed(docs))
# Compare all pairs
for i in range(len(vecs)):
    for j in range(i+1, len(vecs)):
        sim = float(np.dot(vecs[i], vecs[j]) / (np.linalg.norm(vecs[i]) * np.linalg.norm(vecs[j])))
        if sim > 0.95:
            print(f"Duplicate: {docs[i][:50]} <-> {docs[j][:50]} (sim={sim:.3f})")
```

### Recipe 5: Hybrid Dense + Sparse Search
```python
from fastembed import TextEmbedding, SparseTextEmbedding

dense_model = TextEmbedding("BAAI/bge-small-en-v1.5")
sparse_model = SparseTextEmbedding("prithvida/Splade_PP_en_v1")

# Embed with both
dense_vec = next(dense_model.embed(["document text"]))
sparse_vec = next(sparse_model.embed(["document text"]))

# Store both vectors, search with weighted combination
# Dense captures "meaning", sparse captures exact keywords
```

## Industry Expert and Cutting-Edge Usage

**Qdrant's own recommendation:** Use FastEmbed as the default embedding layer for any
Qdrant-based retrieval system. Their examples, tutorials, and quickstarts all use FastEmbed
rather than sentence-transformers.

**RAG pipelines:** FastEmbed is becoming the standard lightweight embedder for
Retrieval-Augmented Generation. LangChain and LlamaIndex both support it as a
provider, and it's preferred for CPU-only deployments (serverless, edge, VPS).

**Hybrid retrieval pattern:** The cutting-edge approach combines FastEmbed dense vectors
with SPLADE sparse vectors. Dense handles semantic similarity, sparse handles exact keyword
matching. Qdrant supports this natively with named vectors. This outperforms either alone
by 5-15% on retrieval benchmarks.

**Matryoshka embeddings:** Some newer models (nomic-embed) support truncating the vector
to fewer dimensions while retaining most quality. A 768-dim vector truncated to 256-dim
retains ~95% of retrieval quality with 3x less storage. FastEmbed supports this when the
underlying model does.

**Multi-vector (ColBERT) re-ranking:** Use FastEmbed's LateInteractionTextEmbedding for
second-stage re-ranking after a fast first-stage dense retrieval. This is the pattern used
in state-of-the-art retrieval systems: fast recall with dense vectors, precise ranking with
late interaction.

**EOS-specific frontier:** The current EOS setup uses symmetric embedding (embed() for both
queries and documents). Switching to asymmetric (query_embed for queries, passage_embed for
documents) would improve retrieval quality for the BGE model family, which was trained with
instruction prefixes.

---

## EOS Usage Patterns

### Two-module architecture
- `eos_ai/embedder.py` — Simple singleton for in-process comparisons (skill matching, memory search).
  Returns numpy arrays. Used by `skill_registry.py`.
- `eos_ai/embedding_engine.py` — Production-grade three-tier engine with graceful degradation.
  Returns Python lists. Used by `memory.py` for Neon storage and retrieval.

### Key constants
- Model: `BAAI/bge-small-en-v1.5`
- Dimensions: 384
- Input guard: `text[:8000]` (embedding_engine.py)
- Backfill rate limit: 1 second pause every 20 rows
- Neon table: `embeddings` with `vector(384)` column

### Why bge-small was chosen
- 384 dimensions keeps pgvector index small and fast
- ~33MB model fits in Docker containers without bloat
- ~150MB runtime memory leaves room for Ollama and other services
- Strong English retrieval performance (MTEB benchmark top-20 in its size class)
- No GPU required — critical for EOS VPS deployment

## Gotchas

### WebSearch denied during research
Context7 and WebSearch were both unavailable during initial skill research. Content is based on
installed package introspection (fastembed 0.8.0), codebase analysis, and existing model knowledge.
Update this skill when web research becomes available for version-specific changelog details.

### fastembed not in eos_ai requirements, only services requirements
`fastembed` is listed in `services/requirements.txt` but not in a top-level requirements.txt.
If running embedding code outside the Docker container, install manually:
`pip install fastembed --break-system-packages`.

### Dimension mismatch is silent until query time
Storing 384-dim (fastembed) and 768-dim (Gemini fallback) vectors in the same pgvector column
does not error on INSERT. It errors on cosine distance queries. The `embedding_model` column
exists to track this, but queries do not filter by it automatically.
