# Tool Mastery Manager — First Operator Pass (Backlog Audit)

**Date:** 2026-04-08
**Operator:** Developer Agent (Claude Opus 4.6)
**Source:** `python3 scripts/tool_mastery_manager.py backlog`
**Artifacts:** `logs/tool_mastery_manager/backlog-2026-04-08T22-39-53Z.{md,json}`
**Status:** audit only — no fixes applied. Awaiting approval.

---

## 1. Backlog Summary

**Total items:** 10 — `invalid=7, missing=3, partial=0, stale=0`

| # | Tool | Status | Source | Why Surfaced |
|---|------|--------|--------|--------------|
| 1 | `goviralbitch` | missing | claude_json | No `skills/tools/goviralbitch/SKILL.md` on disk |
| 2 | `notebooklm_mcp` | missing | claude_json | No `skills/tools/notebooklm_mcp/SKILL.md` on disk |
| 3 | `stitch` | missing | claude_json | No `skills/tools/stitch/SKILL.md` on disk |
| 4 | `voice_pipeline` | invalid | skills_dir | 1 hard failure — `SKILL.md` missing `## Authentication` |
| 5 | `higgsfield` | invalid | skills_dir | 13 failures in `references/best_practices.md` (heading name mismatch) |
| 6 | `fl_studio` | invalid | skills_dir | 13 failures in `references/best_practices.md` (numbered-heading mismatch) |
| 7 | `brave_search` | invalid | skills_dir | 19 failures — `## Section N: …` vs canonical `## …` |
| 8 | `remotion` | invalid | skills_dir | 19 failures — same `## Section N:` pattern |
| 9 | `shadcn_ui` | invalid | skills_dir | 19 failures — same `## Section N:` pattern |
| 10 | `whop` | invalid | skills_dir | 17 failures — **genuinely thin** file (only 4 H2s: tiered structure, not per-section) |

---

## 2. Failure Mode Classification

The 7 `invalid` tools split cleanly into **three remediation tiers**:

### Tier A — Heading Rename (cheap, mechanical)
Files are content-rich (800–1000 lines) but the researcher emitted non-canonical heading names. Verifier requires exact H2 strings like `## Authentication`; files have variants.

| Tool | Actual Pattern | H2 Count | Remediation |
|---|---|---|---|
| `brave_search` | `## Section 1: Authentication` | 21 | rename H2s to canonical |
| `remotion` | `## Section N: …` | 21 | rename H2s to canonical |
| `shadcn_ui` | `## Section N: …` | 19 | rename H2s to canonical |
| `fl_studio` | `## 4. Authentication` | 24 | rename H2s to canonical |
| `higgsfield` | mix — missing 10 sections genuinely | 29 | rename + **fill gaps** for Error Codes, Anti-Patterns, Data Model, Limits, Cost Model, Version Pinning, Design Intent, Problem-Solution Map, Operational Behavior, Ecosystem Position |

### Tier B — Single-Section Patch (trivial)
| Tool | Fix |
|---|---|
| `voice_pipeline` | Add `## Authentication` block to `SKILL.md` (explain: local libraries, no auth — document explicitly) |

### Tier C — Genuine Content Gap (research required)
| Tool | Condition |
|---|---|
| `whop` | File has only 4 H2s (`Tier 1`, `Tier 2`, `EOS Usage Patterns`, `Gotchas`). Structure doesn't map to canonical schema. Needs full research pass. |

### Tier D — Missing Scaffolds (research required)
| Tool | Notes |
|---|---|
| `goviralbitch` | Discovered via `claude_json`. Unknown what this refers to — needs identification before research. |
| `notebooklm_mcp` | MCP server already instrumented in this session (`mcp__notebooklm-mcp__*`). Research path: wrap existing MCP capabilities as skill. Lowest-risk of the three missings. |
| `stitch` | MCP present (`mcp__stitch__*`) — Figma-adjacent design tool. Research path: document the 10+ MCP tools into a canonical skill. |

---

## 3. Prioritized Remediation Plan

Priority order uses: **(cost to fix) × (unblock value)**. Cheap + high-value first.

### P0 — Immediate (≤15 min, no research, no approvals beyond this audit)
1. **`voice_pipeline`** — single `## Authentication` stub declaring "local libraries, no auth required". One-line content fix.
2. **`brave_search`** — `sed`-style H2 rename (`## Section N: X` → `## X`). Content already present. Then re-verify.
3. **`remotion`** — same rename pattern.
4. **`shadcn_ui`** — same rename pattern.

Expected outcome: backlog drops from 10 → 6 in one pass.

### P1 — Same-day (≤45 min, mechanical + minor content)
5. **`fl_studio`** — rename numbered H2s (`## 4. Authentication` → `## Authentication`). Confirm all canonical sections map. Ship.
6. **`higgsfield`** — rename existing H2s, then author 10 missing canonical sections using what's already present in the body (Configuration Patterns, Error Handling, Webhooks/Events, etc. already exist under different names; only a few are genuinely absent).

Expected outcome: backlog 6 → 4.

### P2 — Research flow required (queue, don't block)
7. **`notebooklm_mcp`** — research-lite. MCP tool surface is enumerable from live config; scaffold skill from `mcp__notebooklm-mcp__*` tool list + NotebookLM public docs. Dispatch via `scripts/tool_mastery_research_dispatcher.py`.
8. **`stitch`** — same shape as notebooklm: enumerate `mcp__stitch__*` tools + Stitch public docs. Dispatch research.
9. **`whop`** — external SaaS (creator commerce). Requires full web-research pass for auth, rate limits, webhooks, cost model. Dispatch research.

### P3 — Investigate before research
10. **`goviralbitch`** — unknown provenance. **Do not research yet.** First determine: is this a real tool, a test fixture, a stale config entry, or a typo? If stale, remove from `claude_json` discovery source rather than scaffold a skill for nothing.

---

## 4. Recommended Next Actions (Per Item)

| # | Tool | Action | Tier | Est. Effort |
|---|------|--------|------|---|
| 1 | voice_pipeline | **repair existing skill** — add Authentication stub | B | 2 min |
| 2 | brave_search | **repair existing skill** — H2 rename | A | 3 min |
| 3 | remotion | **repair existing skill** — H2 rename | A | 3 min |
| 4 | shadcn_ui | **repair existing skill** — H2 rename | A | 3 min |
| 5 | fl_studio | **repair existing skill** — H2 rename | A | 5 min |
| 6 | higgsfield | **repair + partial author** — rename + fill ~5 canonical gaps from existing body | A | 15 min |
| 7 | notebooklm_mcp | **queue research** — MCP-anchored, fast turnaround | D | dispatcher |
| 8 | stitch | **queue research** — MCP-anchored, fast turnaround | D | dispatcher |
| 9 | whop | **queue research** — full external web research | C | dispatcher |
| 10 | goviralbitch | **investigate provenance first** — may be **defer + remove discovery source** rather than scaffold | D | 5 min |

---

## 5. What Can Be Fixed Immediately vs. What Needs Research

**Immediate (no research — 6 items, ~30 min total):**
- voice_pipeline, brave_search, remotion, shadcn_ui, fl_studio, higgsfield

**Requires research dispatcher (3 items):**
- notebooklm_mcp (MCP-anchored, fast)
- stitch (MCP-anchored, fast)
- whop (full web research, slow)

**Requires investigation before any action (1 item):**
- goviralbitch

---

## 6. Validation of the Manager Itself

This pass proves the Tool Mastery Manager is **working as intended**:

- **Discovery is real** — it found tools from both `skills_dir` and `claude_json` sources.
- **Verifier is strict** — which is correct; the `## Section N:` pattern is a genuine schema violation even if content is present. This catches researcher drift.
- **Backlog reproducibility** — two runs 22 minutes apart produced identical counts (`invalid=7, missing=3`). Deterministic.
- **One latent weakness found** — the verifier cannot distinguish "heading rename" from "content missing". `brave_search` has full Authentication content but still reports `## Authentication` missing. Consider adding a fuzzy-match hint to verifier output (out of scope for this pass — file as backlog item for the Manager itself).

---

## 7. Approval Gate

**No changes made yet.** Awaiting approval to proceed.

Recommended batching:
- **Batch 1 (P0):** voice_pipeline + brave_search + remotion + shadcn_ui → one commit
- **Batch 2 (P1):** fl_studio + higgsfield → one commit
- **Batch 3 (P2):** dispatch research for notebooklm_mcp + stitch + whop
- **Batch 4 (P3):** investigate goviralbitch, then decide

Approve any subset (e.g., "do Batch 1 only") or the whole sequence.
