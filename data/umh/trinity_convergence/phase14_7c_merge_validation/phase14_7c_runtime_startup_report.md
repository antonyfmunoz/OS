# Phase 14.7C — Runtime Startup Report

## Docker Container: os-operator
- **Port**: 8091
- **Status**: Running
- **Restart**: `docker restart os-operator` — clean startup
- **Python**: 3.11 (Docker image)
- **Mount**: /opt/OS bind-mounted

## Route Module Loading
All 3 route modules imported and mounted successfully:

| Module | Routes | Mount Point | Status |
|--------|--------|-------------|--------|
| cockpit_operator_loop_routes.py | 11 | /api/umh/operator-loop/* | LOADED |
| cockpit_reality_model_routes.py | 15 | /api/umh/reality-model/* | LOADED |
| cockpit_self_improvement_routes.py | 9 | /api/umh/self-improvement/* | LOADED |
| **Total** | **35** | | **ALL LOADED** |

## Authentication
- **Method**: X-Operator-Token header
- **Token source**: UMH_OPERATOR_TOKEN env var
- **Verified**: All protected routes return 403 without token, 200 with token

## GET Endpoint Validation (all 200)

### Operator Loop (5/5 GET routes tested)
- operator-loop/status — 200
- operator-loop/pending-approvals — 200
- operator-loop/active-packets — 200
- operator-loop/audit-trail — 200
- operator-loop/packet/{id} — 200

### Reality Model (12/12 GET routes tested)
- reality-model/status — 200
- reality-model/canonical/patterns — 200
- reality-model/canonical/pattern/{name} — 200
- reality-model/canonical/search — 200
- reality-model/canonical/domains — 200
- reality-model/canonical/stats — 200
- reality-model/canonical/relationships/{name} — 200
- reality-model/instance/observations — 200
- reality-model/instance/recent — 200
- reality-model/instance/search — 200
- reality-model/instance/domains — 200
- reality-model/instance/stats — 200

### Self-Improvement (5/5 GET routes tested)
- self-improvement/status — 200
- self-improvement/cadence-status — 200
- self-improvement/recent-outcomes — 200
- self-improvement/verification-log — 200
- self-improvement/feedback-loop — 200

## System Health at Startup
- CPU: 19-34% (varying)
- RAM: 23-24%
- Agents: 0 active
- Tasks: 0 active
- Mesh: 4 nodes
- API: green
- WS: green
- Organism: CONNECTED, tick #3, 33 events, 24 nodes/18 healthy
