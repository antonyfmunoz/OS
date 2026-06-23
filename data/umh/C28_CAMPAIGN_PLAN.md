# C28 — Cockpit Supremacy / Meta IDE Daily Driver Replacement

## Context

C27 proved ecosystem coherence (CONDITIONAL PASS — Gate 4 Coherence 100%). The organism is alive and data-rich. But 22.8% operational rate against PRD scope and multiple partial subsystems mean the cockpit cannot yet replace Antony's current workflow.

**The competitive bar:** Cockpit must beat ChatGPT (continuity), Claude Code (execution routing), Termius (environment access), Cursor/VS Code (development flow), and Replit (live preview). If UMH is slower, less clear, or less reliable than the current stack, Antony routes around it. Then it fails.

**The acceptance test:** For 10 consecutive real development tasks, Antony never feels compelled to leave the cockpit because leaving would be slower than staying.

**The primary metric: Operator Escape Rate** — how many times Antony had to leave the cockpit to complete a task. Every escape to Termius, Claude Code, Cursor, GitHub, Fly dashboard, or Google Drive is a failure. Target: < 10%. Eventually < 5%. Then ≈ 0%.

**The #1 deliverable: Resume Exactly Where I Left Off** — this is where ChatGPT, Cursor, and Termius all lose. When Antony returns after 10 minutes, 2 hours, or 3 days, the cockpit immediately shows what was active, what happened, what's pending, and offers one-click resume. Continuity becomes native.

---

## Certification Harness Rule (NON-NEGOTIABLE)

**API test = brain works. Browser test = workstation works. C28 certifies the workstation.**

All acceptance testing MUST be browser-driven through the live cockpit UI. No direct API validation counts as operator readiness. API checks are allowed ONLY as supporting diagnostics after a UI failure.

The browser evidence collector is a **permanent Meta IDE subsystem**, not a throwaway test script. It serves three purposes:
1. **Proof packages** — after any cockpit-affecting execution, runs Playwright to generate screenshot/console/network evidence
2. **Regression detection** — organism tick runs lightweight smoke suite to detect deploy breakage
3. **Acceptance runs** — populates the currently-empty `operator-acceptance/runs` endpoint with real browser-driven results

### What counts as a pass
- Playwright opens universalmetaharness.tech
- Authenticates through Clerk (real session)
- Sends prompt in RightRail chat
- Clicks plan/proof/preview/approval controls
- Navigates panels via LeftRail and CommandPalette
- Inspects preview iframe content
- Captures screenshot evidence at each step
- Records console/network errors
- Logs every operator escape

### What does NOT count
- `curl localhost:8091/api/umh/...` returning 200
- JSON payload inspection
- Import checks or unit test green

### Test path
```
Playwright opens Cockpit → logs in via Clerk → sends prompt in RightRail chat
→ observes response → clicks plan/proof/preview controls → verifies UI state
→ screenshots evidence → records pass/fail/gap → logs escape if operator leaves
```

---

## Phasing

### Phase 0 — Critical Bug Fixes (blocks everything)

**0.1** Fix `gated_subprocess_run` imports in cockpit_core_routes.py (5 sites) and workload_runner.py (1 site)
**0.2** Fix `find /app` timeout in operational_truth.py — replace 3 find calls with bounded listing
**0.3** Split cockpit_core_routes.py (2,656 lines) into 6 focused route files
**0.4** Contextual Title Bar — remove "UMH" branding, add: project, branch, active panel, executor status, trust indicator, command palette trigger
**0.5** LivePreview sandbox fix — add `allow-same-origin`

### Phase 1 — Trust & Governance Wiring

**1.1** Trust score JSONL persistence (survive restarts)
**1.2** Wire policy engine to runtime (fix "not available")
**1.3** Wire 9 orphaned panels into routes.ts + Shell.tsx

### Phase 2 — Live Preview System (beats Replit)

**2.1** Projection URL registry with preview_url, health_url
**2.2** Viewport selector: Mobile (375×812), Tablet (768×1024), Desktop (1440×900)
**2.3** Enhanced LivePreview with expand/collapse to full editor surface
**2.4** Preview proxy if cross-origin blocked

### Phase 3 — Real Executor Wiring (beats Claude Code)

**3.1** Executor visibility: SIMULATION (yellow) vs LIVE (green) badge on all execution UI
**3.2** Default executor preference: WorkstationExecutor → AgentExecutor → SimulationExecutor
**3.3** Execution ledger (JSONL source of truth for all executions)
**3.4** Live log streaming via WebSocket

### Phase 3.5 — Workspace Context Layer (makes cockpit feel alive)

**3.5.1** Workspace state as first-class reactive runtime: active_project, active_repo, active_branch, active_file, active_preview, active_execution, active_plan, active_packet
**3.5.2** Wire workspace context into title bar: `CreatorOS · main · LivePreview.tsx · LIVE • Beast · L5 Certified`
**3.5.3** Context-linked relationships: file→preview, file→execution, branch→plan

### Phase 4 — Proof & Review Completion (closes the engineering loop)

**4.1** Browser evidence collector — PERMANENT Meta IDE subsystem (`substrate/meta_ide/browser_evidence_collector.py`). Playwright-based, Clerk-authenticated, callable from proof pipeline + organism tick + certification harness.
**4.2** Proof generation from execution — auto-generate proof with browser evidence for UI-touching changes
**4.3** Wire operator-acceptance/runs — populate with real browser-driven test results
**4.4** Proof review UI — diff viewer, screenshot gallery, approve/reject
**4.5** Proof persistence — JSONL + evidence artifacts

### Phase 5 — Workstation Continuity (THE #1 DELIVERABLE)

**5.1** Active work state snapshot — compose from workspace context + continuity modules
**5.2** Resume card:
```
You were working on:        CreatorOS
Objective:                  Build preview viewport selector
Current file:               LivePreview.tsx
Branch:                     feature/preview-selector
Last execution:             WorkstationExecutor on Beast — Succeeded 43 min ago
Pending review:             Proof Package #194
Next recommended action:    Approve proof and deploy preview service
```
One click: **Resume** — restores full context
**5.3** Session handoff across time gaps (10min → 3 days)

### Phase 6 — Voice-First Command Path

**6.1** Browser STT integration (Electron Speech API or WebSocket fallback)
**6.2** Intent routing: voice → classify → handler
**6.3** Voice command history (last 20)
**6.4** Graceful degradation when Beast/Kokoro offline

### Phase 7 — Beast Node Agent

**7.1** Beast health reporting via mesh
**7.2** Job dispatch to Beast via WorkstationExecutor
**7.3** Artifact retrieval back to VPS

### Phase 8 — Full Surface Certification (browser-driven)

**8.1** Certification suite built ON Phase 4 browser evidence collector
**8.2** Panel surface audit — every primary panel tested through Playwright
**8.3** 10 real task acceptance test:
1. Bug fix (COS/EOS)
2. New feature
3. Config change + deploy
4. Code review
5. Proof review + approval
6. Multi-project context switch
7. Voice-initiated task
8. Resume after break
9. Emergency response
10. End-of-day review

**8.4** Operator Escape Rate calculation (target < 10%)
**8.5** Certification report with full evidence package → Discord

---

## Dependency Graph

```
Phase 0 ─── BLOCKS EVERYTHING
    ├── Phase 1 → Phase 4 (trust → proof loop)
    ├── Phase 2 (live preview — independent)
    ├── Phase 3 → Phase 3.5 → Phase 7 (executor → workspace → Beast)
    ├── Phase 6 (voice — independent)
    ├── Phase 5 (#1 deliverable — needs 1-4 + 3.5)
    └── Phase 8 (certification — needs ALL)
```

---

## Acceptance Criteria

| Criterion | Metric |
|-----------|--------|
| **Operator Escape Rate** | **< 10%** |
| **Resume works** | Leave → return → one-click resume with full context |
| **All acceptance browser-driven** | Playwright against live cockpit — no API-only passes |
| Workspace context live | Title bar shows project/repo/branch/file/executor reactively |
| Critical bugs fixed | 0 NameErrors, 0 timeouts, 0 crashes |
| Trust persists | Scores survive restart |
| Governance wired | Policy engine returns real data |
| Live preview works | iframe + viewport switches + expand/collapse |
| Real executor default | SIMULATION clearly labeled |
| Proof loop complete | Generate → review → approve → persisted |
| Voice usable | Push-to-talk → intent → response |
| Beast connected | Health visible, jobs dispatchable |
| No dead primary buttons | Every primary panel functional |
| 10-task acceptance | 10 tasks, Antony never leaves because staying is faster |
| Zero console errors | Playwright captures — 0 unhandled |
| Screenshot evidence | Every step has proof |

---

## What C28 Proves

```
C24: UMH can produce software                              ✅
C25: UMH can operate through its cockpit loop               ✅
C26: UMH verifies reality and detects divergence            ✅
C27: UMH ecosystem is coherent under operator entropy       ✅ (conditional)
C28: Cockpit replaces ChatGPT+Claude Code+Termius workflow  ⬜
```

The Meta IDE is the factory. C28 finishes the factory.

*v3 — Added: Certification Harness Rule (browser-driven, not API), browser evidence collector as permanent Meta IDE subsystem, Phase 4 engineering loop integration*
