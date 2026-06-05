# Phase 14.7B — Existing Code Mapping

## Pre-14.7B State
Cockpit panels existed as passive dashboard displays.
14.7A delivered 35 backend routes across 3 route modules.
Frontend panels showed data but had no operator controls.

## Backend Routes (from 14.7A)

### Operator Loop Routes (cockpit_operator_loop_routes.py)
11 routes: submit-intent, approve, reject, execute, complete,
status, pending-approvals, active-packets, packet/{id}, audit-trail, audit-log

### Reality Model Routes (cockpit_reality_model_routes.py)
15 routes: snapshot, active-decisions, pending-decisions, resolve-decision,
ratify-decision, submit-observation, query, divergence, coherence-score,
source-truth/{domain}, fork-decision, merge-decision, history, diff, validate

### Self-Improvement Routes (cockpit_self_improvement_routes.py)
9 routes: status, cadence-status, recent-outcomes, verification-log,
feedback-loop, assimilate-outcome, verify-outcome, generate-follow-up, feed-cadence

## Frontend Stores (pre-14.7B)
- agentStore.ts — fetchAgents, controlAgent, handoff, sendSignal
- taskStore.ts — fetchTasks, fetchWorkflows, triggerWorkflow
- executionStore.ts — start/stop/pause/resume, fetchStatus, fetchLog
- approvalStore.ts — fetchApprovals, approve, deny
- knowledgeStore.ts — fetchObservations, fetchMemory, fetchSkills, fetchTracking
- editorStore.ts — fetchFileTree, fetchFileContent, saveFile
- operatorExperienceStore.ts — voice/text commands, DEX responses

## Frontend Stores (added in 14.7B)
- operatorLoopStore.ts — wires all operator-loop + self-improvement routes
- providerRegistryStore.ts — provider registry with smoke testing

## Panel Upgrades (14.7B)
| Panel | Before | After |
|-------|--------|-------|
| AgentsPanel | 126 lines, view-only | 202 lines, controls + handoff + signal |
| UniversalWorkPanel | 248 lines, simple list | 498 lines, 3-view Kanban + create + lifecycle |
| EditorPanel | 210 lines, editor only | 309 lines, + provider registry sidebar |
| KnowledgePanel | 252 lines, 4 tabs | 335 lines, + reality model tab |
| SelfBuildPanel | 244 lines, view-only | 295 lines, + self-improvement section |
