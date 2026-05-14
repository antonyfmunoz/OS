---
name: fastembed
description: "Use when generating vector embeddings for semantic search, skill matching, knowledge retrieval, or similarity comparison — any task requiring text-to-vector conversion."
allowed-tools: "Read, Bash"
version: 1.0
source_url: "https://github.com/qdrant/fastembed"
last_researched: "2026-04-06"
instantiated_from: templates/tools/_template/
api_version: "N/A"
sdk_version: "fastembed 0.8.0"
speed_category: medium
trigger: both
effort: low
context: fork
---

# Tool: FastEmbed

## What This Tool Does

FastEmbed is a lightweight, CPU-optimized Python library from Qdrant for generating dense text
embeddings using ONNX Runtime. No GPU required. No API keys. No network calls. Runs entirely
local with sub-millisecond per-document embedding after model warmup.

Core capabilities used by EOS:
- **Dense text embedding** — convert any text to a fixed-dimension float vector for semantic comparison
- **Batch embedding** — embed thousands of documents efficiently with configurable batch size and parallelism
- **Query vs document embedding** — separate methods for asymmetric retrieval (query_embed vs passage_embed)
- **Multiple model support** — 30+ pre-trained models from 384-dim to 1024-dim
- **Sparse embedding** — BM25-style sparse vectors via SparseTextEmbedding (not used in EOS currently)
- **Image embedding** — CLIP-based image vectors via ImageEmbedding (not used in EOS currently)

## EOS Integration

### Two embedding modules (both use FastEmbed)

**`eos_ai/embedder.py`** — Lightweight singleton used by `skill_registry.py` and `memory.py`.
- Module-level `_model` singleton loaded once per process
- Exposes `embed(text)`, `cosine_similarity(a, b)`, `serialize(vec)`, `deserialize(blob)`
- Returns L2-normalized 384-dim numpy arrays (dot product == cosine similarity)
- Used for: skill matching in SkillRegistry, semantic search in AgentMemory

**`eos_ai/embedding_engine.py`** — Three-tier hybrid embedding with graceful degradation.
- Tier 1: FastEmbed local (free, 384-dim) — primary
- Tier 2: Gemini text-embedding-001 (cloud, paid, 768-dim) — fallback
- Tier 3: Keyword matching (no embedding, returns None) — always works
- Used for: interaction embedding + storage in Neon, semantic search across interactions
- Pre-warms FastEmbed model at init to surface errors early, not on first call
- Stores embeddings in Neon `embeddings` table with `embedding_model` column tracking which tier was used

### Consumers
- **`eos_ai/skill_registry.py`** — On init, embeds every skill's name + first 800 chars via `embedder.embed()`.
  `get_relevant_skills()` uses cosine similarity to match task descriptions to skills. Falls back to keyword
  overlap when embeddings unavailable.
- **`eos_ai/memory.py`** — `semantic_search()` embeds query via EmbeddingEngine, runs pgvector cosine distance
  against stored interaction embeddings.
- **`eos_ai/embedding_engine.py`** — `embed_interaction()` stores vectors in Neon after every interaction.
  `backfill_missing()` bulk-embeds historical interactions without embeddings.

### Model in use
`BAAI/bge-small-en-v1.5` — 384 dimensions, ~33MB ONNX model, cached after first download.
Chosen for: small footprint, fast inference, strong English retrieval performance, no GPU needed.

## Authentication

N/A — FastEmbed runs entirely local. No API keys, no accounts, no network auth.
Models are downloaded from HuggingFace Hub on first use and cached locally in
`~/.cache/fastembed/` (or the path specified by `cache_dir` parameter).

## Quick Reference

### Embed a single text (EOS pattern)
```python
from eos_ai.embedder import embed, cosine_similarity
vec = embed("analyze this lead who feels stuck")  # np.ndarray, 384-dim, L2-normalized
```

### Compare two texts
```python
from eos_ai.embedder import embed, cosine_similarity
a = embed("sales pipeline optimization")
b = embed("improving lead conversion rates")
sim = cosine_similarity(a, b)  # float in [-1, 1], typically 0.3-0.9 for related text
```

### Raw FastEmbed usage (outside EOS wrappers)
```python
from fastembed import TextEmbedding

model = TextEmbedding("BAAI/bge-small-en-v1.5")  # downloads on first call, cached after

# Embed documents (returns generator of numpy arrays)
embeddings = list(model.embed(["first doc", "second doc"]))  # list[np.ndarray]

# Embed a query (adds "query: " prefix for asymmetric retrieval)
query_vecs = list(model.query_embed("search query"))

# Batch with parallelism
embeddings = list(model.embed(large_list, batch_size=256, parallel=4))
```

### Three-tier embedding (EOS pattern)
```python
from eos_ai.embedding_engine import EmbeddingEngine
engine = EmbeddingEngine()

# Automatically tries fastembed -> Gemini -> returns None
vec = engine.embed("some text")           # list[float] or None
tier = engine.get_active_tier()            # 'fastembed (local)' | 'gemini (cloud fallback)' | 'keyword matching'
ok = engine.embed_interaction(iid, text, org_id)  # embed + store in Neon
results = engine.semantic_search("query", org_id, limit=5)  # cosine search against stored embeddings
```

### Supported models (30+ available)
```python
from fastembed import TextEmbedding
models = TextEmbedding.list_supported_models()
# Key models:
# BAAI/bge-small-en-v1.5  — 384-dim (EOS default, fast, small)
# BAAI/bge-base-en-v1.5   — 768-dim (better quality, 3x larger)
# BAAI/bge-large-en-v1.5  — 1024-dim (best quality, 10x larger)
# snowflake/snowflake-arctic-embed-s — 384-dim (competitive alternative)
# sentence-transformers/all-MiniLM-L6-v2 — 384-dim (classic baseline)
# nomic-ai/nomic-embed-text-v1.5 — 768-dim (strong all-rounder)
```

### Serialize for storage
```python
from eos_ai.embedder import serialize, deserialize
blob = serialize(vec)      # bytes for SQLite BLOB
vec = deserialize(blob)    # back to np.ndarray
```

## Conceptual Model

```
FastEmbed Architecture
  |
  +-- TextEmbedding (dense vectors)
  |     |-- embed(documents)     — document/passage embedding (generator)
  |     |-- query_embed(query)   — query embedding with prefix (generator)
  |     |-- passage_embed(texts) — alias for document embedding (generator)
  |     +-- list_supported_models() — discover available models
  |
  +-- SparseTextEmbedding (sparse vectors — BM25-style)
  |     +-- Not used in EOS currently
  |
  +-- ImageEmbedding (CLIP-based image vectors)
  |     +-- Not used in EOS currently
  |
  +-- LateInteractionTextEmbedding (ColBERT-style)
  |     +-- Not used in EOS currently
  |
  +-- ONNX Runtime (execution backend)
        |-- CPU by default (no GPU drivers needed)
        |-- CUDA provider available if onnxruntime-gpu installed
        +-- Model cached in ~/.cache/fastembed/ after first download

EOS Embedding Flow:
  Text input
    -> embedder.embed() or EmbeddingEngine.embed()
    -> TextEmbedding.embed([text])
    -> ONNX Runtime inference (CPU)
    -> 384-dim float32 numpy array
    -> L2-normalize (embedder.py) or .tolist() (embedding_engine.py)
    -> Store in Neon pgvector / compare with cosine similarity
```

See references/best_practices.md for model selection, performance tuning, and anti-patterns.

## Gotchas

### First call downloads the model (~33MB)
`TextEmbedding("BAAI/bge-small-en-v1.5")` triggers a HuggingFace Hub download on first use.
This blocks for 5-30 seconds depending on connection. EOS pre-warms in `EmbeddingEngine.__init__`
to surface this at startup, not during a user request. If the download fails (no internet on VPS),
FastEmbed is permanently unavailable until the model is manually placed in `~/.cache/fastembed/`.

### embed() returns a generator, not a list
`model.embed(["text"])` returns a generator. You must wrap in `list()` or call `next()`.
Forgetting this and trying to index directly (`model.embed(["text"])[0]`) raises TypeError.
EOS handles this: `embedder.py` uses `next(model.embed([text]))`, `embedding_engine.py` uses
`list(model.embed([text]))`.

### Dimension mismatch between tiers kills pgvector queries
EOS Tier 1 produces 384-dim vectors, Tier 2 (Gemini) produces 768-dim. If the Neon `embeddings`
table stores a mix, cosine distance queries will fail on dimension mismatch. The `embedding_model`
column tracks which model produced each vector — queries should filter or the table should be
re-embedded when switching tiers.

### pip install requires --break-system-packages on system Python
On Debian/Ubuntu with system Python (no venv), `pip install fastembed` fails with
"externally-managed-environment" error. Use `pip install fastembed --break-system-packages`.
This is noted in the EOS `embedder.py` error message.

### ONNX Runtime memory usage
Each model loads into memory once and stays resident. `bge-small-en-v1.5` uses ~150MB RAM.
Larger models (bge-large: ~1.3GB) can cause OOM on constrained VPS instances. EOS chose
bge-small specifically for its low memory footprint.

### Input text silently truncated by tokenizer
Each model has a max token length (512 tokens for bge-small). Text beyond this is silently
truncated — no error, no warning. EOS guards with `text[:8000]` in `embedding_engine.py`
but the real limit is tokenizer-dependent. For long documents, chunk before embedding.

### query_embed vs embed produce different vectors
`query_embed()` prepends "query: " to the input for asymmetric retrieval models like BGE.
Using `embed()` for queries and `query_embed()` for documents inverts the expected similarity
ranking. EOS uses `embed()` for both queries and documents (symmetric), which works but
leaves some retrieval quality on the table.
