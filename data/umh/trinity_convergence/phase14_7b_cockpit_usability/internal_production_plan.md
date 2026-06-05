# Phase 14.7B — Internal Production Plan

## Mission
Make Cockpit the primary internal command surface for UMH by wiring
14.7A backend routes into operator-visible, actionable frontend panels.

## Strategy
Wire existing backend routes into existing frontend panels.
No new panels created. No new backend routes created.
Prefer upgrading existing components over creating new ones.

## Execution Plan

### Gate 0: PR #58 Merge + Preflight
- Merge 14.7A PR to main
- Create 14.7B worktree
- Map 14.7A routes to frontend needs

### Wave 1: Cockpit Command Foundation
- Create operatorLoopStore.ts (Zustand store for all operator-loop routes)
- Create providerRegistryStore.ts (provider registry with smoke testing)
- Rewrite AgentsPanel with controls, signal input, handoff
- Rewrite UniversalWorkPanel with Kanban, create form, lifecycle controls

### Wave 2: Operator Control Loop
- Verify create/approve/reject/execute/complete all work from UI
- Verify approval gates visible and enforceable
- Verify audit trail accessible from detail view

### Wave 3: A2A + Meta IDE + Provider Registry
- CommsPanel already functional (verified, no changes needed)
- Integrate provider registry into EditorPanel right sidebar
- Add provider smoke test capability to Meta IDE

### Wave 4: Memory/Skills + Self-Build Prep
- Add Reality Model tab to KnowledgePanel
- Integrate self-improvement loop into SelfBuildPanel
- Verify proof system visible via agent deliverables and audit trails

## Constraints
- No substrate/ mutations
- No new panels (upgrade existing)
- No database migrations
- No projection-specific features
- All execution gated by operator approval
