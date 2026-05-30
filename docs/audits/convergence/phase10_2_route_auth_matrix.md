# Phase 10.2B — Route Auth Classification Matrix

## Auth Levels
- **NONE**: No authentication required
- **AUTH**: Requires `x-org-id` header (authMiddleware)
- **OPERATOR**: Requires AUTH + org owner verification (operatorGuard)

## Security Fixes Applied

### server.ts auth middleware additions
| Route Pattern | Before | After | Reason |
|---|---|---|---|
| `/execution`, `/execution/*` | NONE | AUTH | Exposes execution state, has start/stop/pause/resume mutations |
| `/settings` | NONE | AUTH | Exposes governance config, has PATCH mutation |
| `/sessions` | NONE | AUTH | Exposes organism session data |
| `/docker` | NONE | AUTH | Exposes container list |
| `/workspaces` | NONE | AUTH | Exposes workspace data |
| `/files` | NONE | AUTH | Exposes filesystem directory listing |
| `/file` | NONE | AUTH | Exposes file content read |

### organism.ts operatorGuard additions
| Route | Before | After | Reason |
|---|---|---|---|
| `POST /organism/control` | AUTH only | OPERATOR | Kill/resume mutation must require operator |

### Phase 10.2 new routes (all OPERATOR)
| Route | Method | Auth | Purpose |
|---|---|---|---|
| `/organism/cadence` | GET | OPERATOR | Cadence mode, policy, run history |
| `/organism/candidate-supply` | GET | OPERATOR | Live candidate discovery results |
| `/organism/sandboxes` | GET | OPERATOR | Active sandbox list |
| `/organism/sandboxes/:id` | GET | OPERATOR | Sandbox detail |
| `/organism/approval-packets` | GET | OPERATOR | Pending approval packets |
| `/organism/approval-packets/:id` | GET | OPERATOR | Approval packet detail |
| `/organism/approval-packets/:id/approve` | POST | OPERATOR | Approve candidate for sandbox execution |
| `/organism/approval-packets/:id/reject` | POST | OPERATOR | Reject candidate |
| `/organism/pr-factory` | GET | OPERATOR | PR factory state and review packets |
| `/organism/production-truth` | GET | OPERATOR | Production truth state (main commit, pending PRs) |

## Complete Route Matrix

### Intentionally Unauthenticated
| Route | Method | Justification |
|---|---|---|
| `/health` | GET | Load balancer / uptime check — returns only `{status, ts}` |
| `/pulse` | GET | System telemetry (CPU/mem/disk) — no sensitive data |
| `/mesh/nodes` | GET | Network topology — Tailscale-internal only |
| `/models` | GET | LLM provider status — public-safe read |
| `/infra` | GET | Infrastructure service status — public-safe read |

### Authenticated (AUTH)
| Route | Method | Purpose |
|---|---|---|
| `/sessions` | GET | Organism sessions |
| `/docker` | GET | Container list |
| `/workspaces` | GET | Workspace list |
| `/files` | GET | Directory listing |
| `/file` | GET | File content read |
| `/execution/status` | GET | Execution slot status |
| `/execution/log` | GET | Execution log |
| `/execution/authority` | GET | Authority class query |
| `/execution/start` | POST | Start execution |
| `/execution/stop` | POST | Stop execution |
| `/execution/pause` | POST | Pause execution |
| `/execution/resume` | POST | Resume execution |
| `/settings` | GET | Model routing, governance, notifications |
| `/settings` | PATCH | Update settings |
| `/governance` | GET | Governor policy |
| `/governance` | PATCH | Update governance |
| `/chat/converse` | POST | Send message to organism |
| `/chat/send` | POST | Send channel message |
| `/chat/history` | GET | Chat history |
| `/observations` | GET | System observations |
| `/memory` | GET | Learning signal memory |
| `/tracking` | GET | Execution economy tracking |
| `/config` | GET | Config read |
| `/config/:key` | GET | Config key read |
| `/config` | PATCH | Config write (+ operatorGuard) |
| `/organism/snapshot` | GET | System state snapshot |
| `/organism/status` | GET | Overall status |
| `/organism/health` | GET | Health metrics |
| `/organism/agents` | GET | Agent list |
| `/organism/deliverables` | GET | Agent deliverables |
| `/organism/learning` | GET | Learning signals |
| `/organism/objectives` | GET | All objectives |
| `/organism/objectives/:id` | GET | Specific objective |
| `/organism/economy` | GET | Economy summary |
| `/organism/economy/records` | GET | Economy record log |
| `/organism/runtimes` | GET | Available runtimes |
| `/organism/supervisor` | GET | Supervisor state |
| `/organism/governor` | GET | Governor state |
| `/organism/governor/escalations` | GET | Escalation log |
| `/organism/advisors` | GET | Advisors |
| `/organism/advisors/tree` | GET | Advisor hierarchy |
| `/organism/approvals` | GET | Approvals |
| `/organism/approvals/count` | GET | Approval count |
| `/organism/handoffs` | GET | Handoff queue |
| `/organism/leverage` | GET | Leverage metrics |
| `/organism/workcells` | GET | Workcells |
| `/organism/delegations` | GET | Handoff alias |
| `/organism/refresh` | POST | Trigger refresh |
| `/organism/handoff` | POST | Queue handoff |
| `/organism/parallel` | POST | Parallel execution |

### Operator-Only (OPERATOR)
All mutations and sensitive intelligence routes require operator guard:

| Route | Method | Purpose |
|---|---|---|
| `/organism/world-model` | GET | Substrate world model |
| `/organism/dependency-graph` | GET | Dependency graph |
| `/organism/contradictions` | GET | Contradiction list |
| `/organism/learning-loop` | GET | Learning loop state |
| `/organism/outcome` | POST | Capture outcome |
| `/organism/memory-promotion` | GET | Memory promotion candidates |
| `/organism/memory-promotion/:id/approve` | POST | Approve memory |
| `/organism/memory-promotion/:id/reject` | POST | Reject memory |
| `/organism/compose` | POST | Compose capability |
| `/organism/execute-plan` | POST | Execute plan |
| `/organism/execution-graph` | GET | Plan graph |
| `/organism/execution-graph/:id` | GET | Plan detail |
| `/organism/execute-plan/:id/approve/:stepId` | POST | Approve plan step |
| `/organism/execute-plan/:id/pending` | GET | Pending plan steps |
| `/organism/trial-status` | GET | Self-improvement trials |
| `/organism/templates` | GET | Template library |
| `/organism/template-candidates` | GET | Template candidates |
| `/organism/template-candidates/:id/approve` | POST | Approve template |
| `/organism/template-candidates/:id/reject` | POST | Reject template |
| `/organism/agent-capabilities` | GET | Agent capabilities |
| `/organism/propagation` | GET | Propagation status |
| `/organism/propagation/:id` | GET | Propagation detail |
| `/organism/template-reuse-proof` | GET | Reuse evidence |
| `/organism/outcomes` | GET | Outcomes log |
| `/organism/outcomes/:id` | GET | Outcome detail |
| `/organism/spine-propagation-status` | GET | Spine propagation |
| `/organism/dispatch-report` | POST | Dispatch report |
| `/organism/reports` | GET | Reports |
| `/organism/chat-history` | GET | Chat history |
| `/organism/approve/:id` | POST | Approve governance item |
| `/organism/deny/:id` | POST | Deny governance item |
| `/organism/kill` | POST | Kill organism |
| `/organism/resume` | POST | Resume organism |
| `/organism/governor/reset` | POST | Reset governor |
| `/organism/control` | POST | Kill/resume via action param |
| `/organism/cadence` | GET | Cadence state |
| `/organism/candidate-supply` | GET | Candidate supply results |
| `/organism/sandboxes` | GET | Sandbox list |
| `/organism/sandboxes/:id` | GET | Sandbox detail |
| `/organism/approval-packets` | GET | Approval packets |
| `/organism/approval-packets/:id` | GET | Approval packet detail |
| `/organism/approval-packets/:id/approve` | POST | Approve for sandbox execution |
| `/organism/approval-packets/:id/reject` | POST | Reject candidate |
| `/organism/pr-factory` | GET | PR factory state |
| `/organism/production-truth` | GET | Production truth state |

## Verdict
All routes exposing internal candidate supply, template governance, PR factory state, sandbox state, manifest state, cadence state, production truth state, and mutation controls now require OPERATOR auth. Privileged mutations return 403 without operator token.
