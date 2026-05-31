# Quick Task 260530-ocp: Phase 13.1 — Voice-First DEX Cockpit Command Layer

## Task 1: Build voice-first DEX cockpit command surface

### Files
- cockpit/src/renderer/operator/voiceTypes.ts (new)
- cockpit/src/renderer/operator/speechInputAdapter.ts (new)
- cockpit/src/renderer/stores/operatorExperienceStore.ts (new)
- cockpit/src/renderer/panels/OperatorPanel.tsx (new)
- cockpit/src/renderer/components/Shell.tsx (edit)
- cockpit/src/renderer/stores/cockpitStore.ts (edit)
- cockpit/src/renderer/types/routes.ts (edit)
- docs/audits/convergence/phase13_1_*.md (new)
- docs/research/cortextos_phase13_runtime_surface_notes.md (new)
- data/umh/operator_experience/phase13_1_*.json (new)

### Action
Build the complete voice-first operator cockpit surface per 15-task spec.

### Verify
- tsc --noEmit passes
- electron-vite build succeeds
- pytest full suite passes (no new failures)
- all pre-commit gates pass
- 23/23 success criteria met

### Done
All 15 tasks completed across 8 atomic commits.
