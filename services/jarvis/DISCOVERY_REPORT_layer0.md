# Jarvis Layer 0 — Discovery Report

**Session:** B (Layer 0 + Protocol Pack + Control Plane)
**Date:** 2026-05-18
**Worktree:** jarvis-layer0

## Environment Discovery

### Python
- Python 3.12 on Linux (VPS)
- Pydantic 2.12.5 — used for all schemas
- FastAPI 0.136.1 — used for API surface
- uvicorn available for serving

### Existing Service Conventions
- **Pattern:** `sys.path.insert(0, "/opt/OS")` at top of service files
- **Env loading:** `load_dotenv("/opt/OS/services/.env")` then `load_dotenv("/opt/OS/runtime/.env", override=True)`
- **FastAPI setup:** `FastAPI(title=..., version=...)` with CORS for localhost:5173 and 100.77.233.50:5173
- **Reference service:** `services/operator_api.py` (FastAPI + uvicorn)
- **Other services:** `goal_api.py` (Flask), `discord_bot.py` (py-cord), various Flask handlers

### Protected Files (NOT modified)
- `eos_ai/gateway.py` — untouched
- `eos_ai/model_router.py` — untouched  
- `eos_ai/memory.py` — untouched
- No existing control plane was overwritten
- No competing execution system created

### Project Config
- `pyproject.toml` declares `universal-meta-harness` package
- `hatchling` build backend
- FastAPI and uvicorn already in `services/requirements.txt`

### No Pre-existing Jarvis
- `/opt/OS/services/jarvis/` did NOT exist before this session
- Created from scratch as new service package

## Architecture Decisions

1. **Pydantic over dataclasses** — Pydantic 2.12.5 available, provides validation, JSON serialization, and schema generation out of box
2. **Required UUID fields for governance/trace on WorkPacket** — type-level enforcement means you literally cannot construct an ungoverned work packet
3. **Pre-creation validation on InvariantChecker** — `validate_pre_creation()` catches missing fields before Pydantic rejects them, giving actionable error messages
4. **Auto-governance for low-risk** — SignalRouter auto-approves NEGLIGIBLE/LOW risk, defers MEDIUM+. Placeholder for real governance engine.
5. **Event bus is in-memory** — appropriate for single-process substrate; upgrade path is clear if needed
