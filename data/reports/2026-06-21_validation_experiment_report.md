# UMH Validation Experiment — Final Report

## Summary

Three deliverables completed in this session:

1. **Browser Gate (Plan C):** VERIFIED 3/3 passes — all 4 layers (DOM, NET, CON, LOG) green across 3 viewports (desktop/tablet/mobile). Five commits fixed NET layer (expanded device roots as browse proof) and LOG layer (Clerk Bearer token auth, browser-first health check, cache across viewports).

2. **E2E Chat Loop (Plan E):** Full loop proven end-to-end — chat → DEX response with suggested actions → Create Work Packets → Engineering Plan → Work panel. Four screenshots captured as evidence.

3. **UMH Validation Experiment (Plan G):** Comparative test proving UMH provides measurable value.

---

## Validation Experiment Results

### Test A — Blind (Context Only, No Tools)
- **Score: 67/100**
- Duration: 47s, 0 tool uses
- Worked purely from CLAUDE.md, memory index, and conversation context

### Test B — Organism (Full Codebase + Runtime Access)
- **Score: 92.3/100**
- Duration: 381s, 35 tool uses
- Evidence-backed: docker ps, query_graph.py, git log, file inspection

### Comparative Scoring (10 Categories)

| Category | Test A | Test B | Delta |
|----------|:------:|:------:|:-----:|
| Architecture Understanding | 8 | 9 | +1 |
| Stage of Development | 7 | 9 | +2 |
| Context Reconstruction | 8 | 10 | +2 |
| Runtime Awareness | 5 | 9 | **+4** |
| Historical Decision Recovery | 9 | 10 | +1 |
| Cockpit Awareness | 6 | 9 | **+3** |
| Meta IDE Awareness | 5 | 9 | **+4** |
| Production Awareness | 5 | 9 | **+4** |
| Accuracy | 7 | 9.3 | +2.3 |
| Actionability | 7 | 9 | +2 |
| **TOTAL** | **67** | **92.3** | **+25.3** |

### Where Context Alone Sufficed (Delta ≤ 1)
- Architecture Understanding — CLAUDE.md documents this thoroughly
- Historical Decision Recovery — laws written with incident dates and rationale

### Where Organism Access Was Decisive (Delta ≥ 3)
- **Runtime Awareness (+4)** — Test B found os-operator UNHEALTHY, organism loop at 34 ticks but 0 messages processed. Invisible without docker ps.
- **Meta IDE Awareness (+4)** — Test B mapped 17 Python files in substrate/meta_ide/, found the 25K-line coordinator. Test A only knew gap closure names.
- **Production Awareness (+4)** — Test B discovered actual container uptimes, Fly.io v360 in LAX, 1Password config. Test A could only list what should be running.
- **Cockpit Awareness (+3)** — Test B counted 42 components, 98 route files, read fly.toml. Test A knew it has panels.

### Key Discovery Only Test B Could Make
The organism loop is alive but empty — 34 ticks completed, 0 messages processed across all 4 workcells. This is exactly what Phase 10.0 is designed to solve.

---

## Final Verdict: B) UMH Provides Measurable Value

The 25.3-point gap (67 to 92.3) IS UMH's value proposition. It's concentrated in operational categories (runtime, production, implementation) where wrong answers cause real damage. The strategic layer (architecture, decisions, priorities) is well-documented enough that context alone works — but the operational layer requires the organism.

## Browser Gate Evidence

| Pass | DOM | NET | CON | LOG |
|------|-----|-----|-----|-----|
| 1/3 | OK | OK | OK | OK |
| 2/3 | OK | OK | OK | OK |
| 3/3 | OK | OK | OK | OK |

Commits: e2d79d8d, b16d308f, 7a815cf1, b634153b, ef8fbd07
