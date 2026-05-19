# Session F — Integration / Model Routing / Launch

**Date**: 2026-05-18
**Session ID**: F
**Branch**: worktree-session-f-integration
**Status**: COMPLETE

## Objective

Integrate the Jarvis MVP pieces from other sessions, create the full 12-label
symbolic model routing config, build launch/smoke-test infrastructure, and
document the integration.

## What Was Found (Discovery)

1. **MVP code lives in `umh_mvp/`** (not `services/jarvis/`) — running from the
   `umh-mvp` worktree. Backend on 8093, frontend on 5173, both live.
2. **All 14 API endpoints** respond correctly (health, signal, traces, resume,
   awareness, capabilities, workpackets, decisions, proofs, ontology, state,
   memory-candidates, memories, pending-approvals).
3. **Existing symbolic router** has 6 labels (reasoning, fast, creative,
   strategic, extraction, classification). Task required 12.
4. **Port 8091** (operator API) and **8092** (operator UI) are occupied and protected.
5. **Tailscale** is active with 4 devices on the private network.
6. **runtime/model_router.py** is protected and must not be modified.

## What Was Built

### Model Routing (`services/jarvis/model_routing/`)

- **capabilities.py**: 12 symbolic capability classes with full metadata
  (provider symbols, fallback chains, privacy levels, cost hints, local-first flags)
- **config.py**: `RoutingConfig` class that maps capability labels to
  `model_router.call_with_fallback()` kwargs with env var overrides

### Integration (`services/jarvis/integration/`)

- **health.py**: `HealthAggregator` — probes backend, frontend, operator API,
  and Ollama in one call
- **cors.py**: `cors_origins()` — generates CORS origin list including all 4
  Tailscale device IPs
- **bridge.py**: `JarvisBridge` — connects symbolic capability labels to
  runtime/model_router.py without modifying it

### Launch (`services/jarvis/launch/`)

- **launch_backend.sh**: Start script with port-conflict detection and import
  verification. Supports foreground and `--bg` modes.
- **smoke_test.py**: 10-point integration test suite covering all endpoints,
  port safety, and routing config validity
- **launch_frontend_notes.md**: Instructions for frontend launch (Windows-side)

### Documentation

- **DISCOVERY_REPORT.md**: Full system state at discovery time
- **README_INTEGRATION.md**: Complete integration guide with architecture,
  quick start, endpoint reference, and routing table
- **PORTS.md**: Port assignments with conflict documentation
- **env.example**: Environment variable template

## Smoke Test Results

```
Jarvis Integration Smoke Test
========================================
  [PASS] backend_health (29ms)
  [PASS] signal_endpoint (3ms)
  [PASS] trace_endpoint (2ms)
  [PASS] resume_endpoint (1ms)
  [PASS] awareness_endpoint (1ms)
  [PASS] capabilities_endpoint (2ms)
  [PASS] frontend_reachable (16ms)
  [PASS] port_8091_untouched (7ms)
  [PASS] port_8092_status (4ms)
  [PASS] routing_config_valid (147ms)

  ALL PASSED (10/10)
```

## Checklist

- [x] Discovery completed
- [x] DISCOVERY_REPORT.md written
- [x] Backend health works
- [x] Frontend can read backend (Vite proxy configured)
- [x] Smoke test passes (10/10)
- [x] Port 8093 in use by Jarvis backend
- [x] Port 8091 untouched (verified by smoke test)
- [x] Port 8092 documented (operator-ui)
- [x] Tailscale IPs documented
- [x] Env variables documented
- [x] Protected files untouched
- [x] 12 capability classes defined
- [x] Local-first routing configured
- [x] Cloud fallback configured (no hardcoded secrets)
- [x] CORS includes Tailscale IPs
- [x] README_INTEGRATION.md written
- [x] All Python files compile clean
- [x] All Python files formatted with ruff

## Files Created

```
services/jarvis/
  __init__.py
  DISCOVERY_REPORT.md
  README_INTEGRATION.md
  SESSION_REPORT.md
  PORTS.md
  env.example
  model_routing/
    __init__.py
    capabilities.py
    config.py
  integration/
    __init__.py
    health.py
    cors.py
    bridge.py
  launch/
    __init__.py
    launch_backend.sh
    launch_frontend_notes.md
    smoke_test.py
```

## Not Done (By Design)

- Did not modify `runtime/model_router.py` (protected)
- Did not install Langfuse (capacity unknown, not required for MVP)
- Did not modify existing `umh_mvp/` code
- Did not change port 8091 or 8092 services
- Did not hardcode any API keys
