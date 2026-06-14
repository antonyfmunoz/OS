# Phase 9 — Command Runtime Proof

## Summary
Built the canonical intent-to-action layer. Every operator surface (voice, cockpit, API, meeting, mobile) routes through one Command Runtime.

## Architecture
- **Composition over creation**: Composes EmpireRouter, WorkPacketEngine, PolicyEngine, ContinuityRuntime, PresenceRuntime, StrategicGapEngine, TickLoop, ProjectionEngine. Zero new execution engines.
- **Deterministic classification**: 60+ regex patterns classify action type from verb patterns. Zero LLM calls in classification path.
- **Full context assembly**: Every command automatically receives profile, session, presence, attention, active objectives, work packets, loops, projections, risks, drift warnings.

## Files Created
| File | Lines | Purpose |
|------|-------|---------|
| substrate/organism/command_runtime.py | 1187 | Core module: 4 enums, 5 dataclasses, CommandClassifier, ContextAssembler, CommandRouter, CommandTimeline, CommandHistory, CommandRuntime |
| tests/test_command_runtime.py | 749 | 91 tests across 15 test classes |
| cockpit/src/renderer/panels/CommandsPanel.tsx | 395 | 5-tab panel: Submit, Active, Pending, Timeline, History |

## Files Modified
| File | Change |
|------|--------|
| transports/api/cockpit_operator_loop_routes.py | +136 lines: 8 API routes |
| substrate/canonical_types.py | +15 type registrations |
| cockpit/src/renderer/stores/cockpitStore.ts | +1 Panel type: 'commands' |
| cockpit/src/renderer/types/routes.ts | +2 lines: Zap icon, route entry key 'z' |
| cockpit/src/renderer/components/Shell.tsx | +3 lines: import + case |

## Canonical Types Registered (15)
CommandActionType, CommandStatus, CommandSource, CommandEventType, CommandContext, Command, CommandEvent, CommandRoutingDecision, CommandClassifier, ContextAssembler, CommandRouter, CommandTimeline, CommandHistory, CommandRuntime

## Command Action Types (11)
query, execute, review, approve, reject, schedule, switch_profile, switch_session, create_objective, create_workpacket, create_sequence

## API Routes (8)
- GET /command/status
- POST /command/submit
- POST /command/classify
- GET /command/history
- GET /command/pending
- GET /command/timeline
- POST /command/{command_id}/approve
- POST /command/{command_id}/reject

## Routing Destinations
| Action | Destination System |
|--------|-------------------|
| query (changes/gone) | continuity_runtime |
| query (status/overview) | empire_router |
| query (risk/threat) | projection_engine |
| query (drift/stuck) | strategic_tick_loop |
| execute | empire_router |
| review | empire_router |
| approve | approval_system |
| reject | approval_system |
| schedule | tick_loop |
| switch_profile | presence_runtime |
| switch_session | presence_runtime |
| create_objective | strategic_gap_engine |
| create_workpacket | empire_router |
| create_sequence | empire_router |

## Test Results
- Phase 9: 91/91 passing
- Regression (Phases 4-8): 281/282 passing (1 pre-existing flaky test on main)
- Total: 372/373 passing

## Deployment
- os-operator: Docker restarted, clean startup, cockpit router mounted
- Cockpit: deployed via `bash cockpit/deploy.sh`, health checks passing
- Pre-commit gates: dependency direction clean, zero violations

## Acceptance Tests
1. ✅ "review operator roadmap" → review workflow (action_type=review, routed to empire_router)
2. ✅ "switch to engineer profile" → profile activation (action_type=switch_profile, routed to presence_runtime)
3. ✅ "create objective: finish workstation" → objective creation (action_type=create_objective, routed to strategic_gap_engine)
4. ✅ "approve packet" → approval (action_type=approve, routed to approval_system)
5. ✅ "what changed while I was gone" → continuity query (action_type=query, routed to continuity_runtime)

## Architecture Validation
- ✅ No duplicate routing systems (uses existing EmpireRouter)
- ✅ No duplicate execution systems (routes into spine, never executes directly)
- ✅ No duplicate approval systems (routes into existing approval_system)
- ✅ All destinations are existing UMH subsystems

## Commit
ef711657 on main, pushed to GitHub.
