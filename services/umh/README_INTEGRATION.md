# UMH Integration Guide

## Overview

UMH is the UMH execution cockpit — a signal-to-outcome pipeline with
governance gates, trace storage, proof artifacts, and memory promotion.

This directory (`services/umh/`) contains the integration, routing,
and launch infrastructure. The core MVP code lives in `umh_mvp/`.

## Architecture

```
Frontend (5173) → API (8093) → Pipeline → Governance → Adapters → Trace → Memory
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Backend API | `umh_mvp/api/` | FastAPI on port 8093 |
| Pipeline | `umh_mvp/engine/` | Signal → outcome execution loop |
| Governance | `umh_mvp/governance/` | Risk-based approval gate |
| Adapters | `umh_mvp/adapters/` | Shell, file execution bridges |
| Layer 0 | `umh_mvp/layer0/` | Ontological primitives and laws |
| Symbolic Router | `umh_mvp/router/` | 6-label capability routing |
| Protocols | `control_plane/protocols/` | Canonical Pydantic types |
| Frontend | `frontend/` | React 19 + Vite 8 + Tailwind 4 |
| **Model Routing** | `services/umh/model_routing/` | 12-label routing config |
| **Integration** | `services/umh/integration/` | Health, CORS, bridge |
| **Launch** | `services/umh/launch/` | Scripts and smoke tests |

## Quick Start

### Backend (VPS)

```bash
# Option 1: Direct
cd /opt/OS
python3 -m uvicorn umh_mvp.api.app:app --host 0.0.0.0 --port 8093 --reload

# Option 2: Launch script
./services/umh/launch/launch_backend.sh

# Option 3: Background
./services/umh/launch/launch_backend.sh --bg
```

### Frontend (any machine with Node.js)

```bash
cd frontend
npm install
npm run dev
```

### Smoke Test

```bash
python3 services/umh/launch/smoke_test.py
```

## Model Routing

### Capability Classes

UMH uses **symbolic capability labels** instead of model names.
Callers request a capability; the router resolves it to a provider.

| Capability | Default Provider | Local? | Use Case |
|-----------|-----------------|--------|----------|
| best_cloud_reasoning | cc_sdk (Opus 4.6) | No | CEO/strategic decisions |
| fast_cloud_reasoning | Gemini Flash | No | Bulk worker tasks |
| cheap_cloud_reasoning | Groq Llama | No | Classification, tagging |
| local_fast_model | Ollama gemma3:4b | Yes | Private data processing |
| local_code_model | Ollama Qwen Coder | Yes | Code gen on private repos |
| local_embedding_model | Ollama nomic-embed | Yes | Vector embeddings |
| local_vision_model | Ollama LLaVA | Yes | Private image analysis |
| local_transcription | Whisper local | Yes | Speech-to-text |
| cloud_vision_model | Gemini Flash Vision | No | Non-private images |
| local_tts_model | Piper TTS | Yes | Text-to-speech |
| cloud_tts_model | ElevenLabs | No | High-quality voice |
| local_stt_model | Whisper local | Yes | Live voice interface |

### Overriding Routes

Set environment variables to override any capability's provider:

```bash
export JARVIS_ROUTE_BEST_CLOUD_REASONING=gemini_flash
export JARVIS_ROUTE_LOCAL_FAST_MODEL=ollama_phi3
```

### Bridge to model_router

The `UMHBridge` class connects symbolic labels to `runtime/model_router.py`:

```python
from services.umh.integration import UMHBridge
from services.umh.model_routing import CapabilityClass

bridge = UMHBridge()
result = bridge.route(
    CapabilityClass.BEST_CLOUD_REASONING,
    system_prompt="You are a strategic advisor.",
    user_prompt="Analyze this market.",
)
```

## Cross-Device Access

Tailscale provides private network access from all devices:

- **Frontend**: `http://100.77.233.50:5173`
- **API Health**: `http://100.77.233.50:8093/api/umh/health`
- **API Docs**: `http://100.77.233.50:8093/docs`

## Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/umh/health` | GET | Backend health check |
| `/api/umh/signal` | POST | Submit a signal to the pipeline |
| `/api/umh/traces` | GET | List execution traces |
| `/api/umh/awareness` | GET | Global system awareness |
| `/api/umh/capabilities` | GET | Routing capabilities |
| `/api/umh/resume` | GET | Workstation resume state |
| `/api/umh/ontology` | GET | Layer 0 primitives and laws |
| `/api/umh/decisions` | GET | Governance decisions |
| `/api/umh/pending-approvals` | GET | Awaiting approval |
| `/api/umh/approve` | POST | Approve a denied signal |
| `/ws` | WebSocket | Real-time event stream |

## Environment Variables

See `env.example` for the full list. Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| JARVIS_BACKEND_PORT | 8093 | Backend API port |
| JARVIS_FRONTEND_PORT | 5173 | Frontend dev port |
| JARVIS_BACKEND_HOST | 0.0.0.0 | Backend bind address |
| JARVIS_CORS_EXTRA_ORIGINS | — | Additional CORS origins |
| JARVIS_ROUTE_* | — | Routing overrides |

## Files

```
services/umh/
  DISCOVERY_REPORT.md        — what we found during discovery
  README_INTEGRATION.md      — this file
  PORTS.md                   — port assignments and conflicts
  env.example                — environment variable template
  model_routing/
    __init__.py
    capabilities.py          — 12 capability class definitions
    config.py                — routing config with env overrides
  integration/
    __init__.py
    health.py                — aggregated health checker
    cors.py                  — Tailscale-aware CORS origins
    bridge.py                — symbolic → model_router bridge
  launch/
    launch_backend.sh         — backend start script
    launch_frontend_notes.md  — frontend launch instructions
    smoke_test.py             — integration smoke test
```
