# Session F — Integration Discovery Report

**Date**: 2026-05-18
**Session**: F (Integration / Model Routing / Launch)
**Worktree**: session-f-integration
**Branch**: worktree-session-f-integration

## 1. System State at Discovery

- **Python**: 3.12.3
- **FastAPI**: 0.136.1, **Pydantic**: 2.12.5, **uvicorn**: 0.42.0
- **Node**: Available (frontend dev server running)
- **Tailscale**: Active — 4 devices on private network

## 2. Live Services

| Port | Service | Status | PID |
|------|---------|--------|-----|
| 8091 | Operator API (Docker) | RUNNING | docker-proxy |
| 8092 | Operator UI (tsx) | RUNNING | node |
| 8093 | Jarvis Backend (uvicorn) | RUNNING | python3 |
| 5173 | Jarvis Frontend (Vite) | RUNNING | node |
| 11434 | Ollama | NOT CHECKED | — |

## 3. Code Locations

The MVP code does NOT live in `services/jarvis/` — it lives in:

- **Backend**: `/opt/OS/.claude/worktrees/umh-mvp/umh_mvp/` (28 Python files)
- **Frontend**: `/opt/OS/.claude/worktrees/umh-mvp/frontend/src/` (19 source files)
- **Protocols**: `control_plane/protocols/` (shared, canonical types)

The `services/jarvis/` directory is used by Session F for:
- Integration layer (health, CORS, bridge)
- Model routing config (12 capability classes)
- Launch scripts and smoke tests
- Documentation

## 4. Existing Symbolic Router

`umh_mvp/router/symbolic.py` has 6 capability labels:
- reasoning, fast, creative, strategic, extraction, classification

Session F extends this to 12 labels with full routing metadata:
- best_cloud_reasoning, fast_cloud_reasoning, cheap_cloud_reasoning
- local_fast_model, local_code_model, local_embedding_model
- local_vision_model, local_transcription_model, cloud_vision_model
- local_tts_model, cloud_tts_model, local_stt_model

## 5. API Endpoints Verified

All endpoints respond correctly:

| Endpoint | Method | Status |
|----------|--------|--------|
| /api/jarvis/health | GET | 200 OK |
| /api/jarvis/signal | POST | 200 OK |
| /api/jarvis/traces | GET | 200 OK |
| /api/jarvis/resume | GET | 200 OK |
| /api/jarvis/awareness | GET | 200 OK |
| /api/jarvis/capabilities | GET | 200 OK |
| /api/jarvis/workpackets | GET | 200 OK |
| /api/jarvis/decisions | GET | 200 OK |
| /api/jarvis/proofs | GET | 200 OK |
| /api/jarvis/ontology | GET | 200 OK |
| /api/jarvis/state | GET | 200 OK |
| /api/jarvis/memory-candidates | GET | 200 OK |
| /api/jarvis/memories | GET | 200 OK |
| /api/jarvis/pending-approvals | GET | 200 OK |

## 6. Tailscale Network

| Device | Tailscale IP | Platform |
|--------|-------------|----------|
| VPS (srv1500858) | 100.77.233.50 | Linux |
| Desktop | 100.74.199.102 | Windows |
| iPad Pro | 100.98.71.38 | iOS |
| iPhone 15 Pro Max | 100.108.75.25 | iOS |

## 7. Protected Files — Verified Untouched

- [x] runtime/model_router.py — NOT in this worktree (expected)
- [x] services/operator_api.py — port 8091 untouched
- [x] docker-compose.yml — not modified
- [x] eos_ai/ — not touched
- [x] runtime/ — not touched

## 8. Integration Architecture

```
┌─────────────────────────────────────────────┐
│  Frontend (React 19 + Vite)  — port 5173    │
│  Views: Dashboard, Signal, Traces,          │
│         WorkPackets, Governance, Awareness   │
└──────────────────┬──────────────────────────┘
                   │ /api/* proxy + /ws
                   ▼
┌─────────────────────────────────────────────┐
│  Backend (FastAPI)  — port 8093             │
│  umh_mvp/api/app.py                        │
│                                             │
│  ┌─────────────┐  ┌──────────────────────┐  │
│  │ Pipeline     │  │ Governance Engine    │  │
│  │ (signal→out) │  │ (risk gate)          │  │
│  └──────┬──────┘  └──────────────────────┘  │
│         │                                    │
│  ┌──────▼──────┐  ┌──────────────────────┐  │
│  │ TraceStore   │  │ MemoryPromoter       │  │
│  │ (in-memory)  │  │ (JSON persist)       │  │
│  └─────────────┘  └──────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│  services/jarvis/  (Session F additions)    │
│                                             │
│  model_routing/                             │
│    capabilities.py  — 12 capability classes  │
│    config.py        — routing config + env   │
│                                             │
│  integration/                               │
│    health.py  — aggregated health checks     │
│    cors.py    — Tailscale-aware CORS         │
│    bridge.py  — symbolic→model_router bridge │
│                                             │
│  launch/                                    │
│    launch_backend.sh   — start backend       │
│    smoke_test.py       — integration tests   │
│    launch_frontend_notes.md                  │
└─────────────────────────────────────────────┘
```
