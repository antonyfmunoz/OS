# UMH Adapter Capability Contracts

**Phase:** 14.6B-UMH
**Status:** DRAFT

## Adapter Protocol

Defined in `adapters/protocol.py`. All adapters implement a common interface contract for initialization, health check, and capability declaration.

## LLM Adapter

`adapters/models/llm_adapter.py` wraps `model_router.py` to provide a unified LLM interface.

- Routes through `call_with_fallback()` with provider chain: cc_sdk --> Gemini 2.5 Flash --> Groq --> Ollama
- Supports `agent_type='ceo'` and `force_opus=True` for strategic routing
- Deterministic fallback for every LLM call (rules/regex/templates before AI)

## Tool Adapters

| Adapter | Purpose |
|---------|---------|
| Filesystem | File read/write/list operations |
| Git | Repository operations, diff, commit |
| Shell | Command execution with sandboxing |
| Tmux | Session management, terminal multiplexing |

## Capability Harnesses

| Harness | Purpose | Status |
|---------|---------|--------|
| Goose | AI coding agent integration | Available |
| UI-TARS | UI automation and testing | Available |
| Kokoro | Voice TTS (82M model on Beast at :8880) | Available |
| Creative gen | Content generation pipeline | Available |

## Google Workspace (GWS) Adapters

| Adapter | Purpose |
|---------|---------|
| GWS Connector | Authentication and API connection management |
| GWS Scanner | Document discovery and metadata extraction |
| Email GPS | Email parsing and signal extraction |
| Doc Creator | Document generation from templates |

## Data Source Adapters

| Adapter | Purpose |
|---------|---------|
| LocalFileSource | `adapters/data_source_adapters/local_file_source.py` -- local file ingestion |
| GWSSource | `adapters/data_source_adapters/gws_source.py` -- Google Workspace ingestion |

Both feed into the canonical ingestion pipeline: perceive --> interpret --> decompose --> bridge --> map --> persist --> query_back.
