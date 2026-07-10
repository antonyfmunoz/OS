---
type: codewiki-dir
dir: .playwright-mcp
---

# `.playwright-mcp/` — Playwright MCP browser debug artifacts (gitignored)

**162 files · 30,269,065 bytes (~30 MB) · rollup category · [Full file inventory](../inventory/dot-playwright-mcp.md)**

## Purpose
`.playwright-mcp/` is the scratch output directory for the Playwright MCP browser tool. When Claude drives a headless (or executor-node) browser during development — DOM checks, cockpit dogfooding, page-structure reads — the MCP server dumps its byproducts here: full-page screenshots (`*.png`) and per-session console logs (`console-<ISO-timestamp>.log`). It is a debug/evidence sink, not source code.

## How it fits
Outside the architecture stack entirely — it is tool output, not code. Nothing in `projections/`, `transports/`, `adapters/`, or `substrate/` imports or reads it. It is classified as a **rollup** in the census (summarized by count/bytes rather than file-by-file inventoried) precisely because it is bulk generated artifact, and it is gitignored so these ~30 MB of images and logs never enter version control.

## Structure
Flat directory, 162 entries, two kinds:

| Kind | Example | Role |
|---|---|---|
| Screenshots | `cockpit-initial.png` | Full-page PNG captures from browser runs |
| Console logs | `console-2026-05-26T23-56-05-790Z.log` | Timestamped browser-console transcripts per session |

The bulk of the ~30 MB is PNG screenshots; the console logs are small text files keyed by ISO timestamp.

## Data & state
Pure generated debug output. Timestamps in filenames span multiple dates (e.g. late May through early June 2026), so it accumulates across sessions and is never auto-pruned. No secrets are *intended* here, but browser console logs and screenshots of the authenticated cockpit could in principle capture session state — treat the contents as sensitive scratch, not shareable evidence.

## Gotchas
- **This is not verification evidence.** Per the Browser Verification Law (`.claude/rules/browser-verification.md`), Playwright MCP run from the orchestrator uses bundled headless Chromium with no real display and produces false-positive results. MCP-on-orchestrator is legitimate only for *development* DOM checks and page-structure reads. Real verification evidence comes from the executor-node path (`browser_evidence_collector.trigger_collection(...)` → mesh daemon → visible Chrome), not from screenshots dumped here.
- The directory grows unbounded and is safe to delete wholesale (`rm -rf .playwright-mcp/`) — it is gitignored scratch with no referenced state. Nothing breaks.
- Because it is gitignored, its size is invisible to `git status` but real on disk (~30 MB) — worth clearing on the lightweight VPS node, which per Node Role Discipline should not hoard debug artifacts.

## See also
- [dot-claude.md](dot-claude.md) — `rules/browser-verification.md` defines the real evidence path
- [nodes.md](nodes.md) — executor-node browser verification (the sanctioned path)
- [health-findings.md](../health-findings.md)
