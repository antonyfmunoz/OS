---
type: codewiki-inventory
dir: .claude
source_sha: 0312cc4e33802424a5a6a5c1807dcd0097e63208
---

# `.claude/` — File Inventory

**Files:** 157 regular + 18 symlinks · **Bytes:** 2,237,329

[Narrative page](../dirs/dot-claude.md)


## .claude/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/CLAUDE.md` | 103 | Developer Agent — .claude Context |
| `.claude/last_cc_version` | 1 | marker file — last seen Claude Code CLI version |
| `.claude/scheduled_tasks.lock` | 1 | lockfile guarding scheduled-task single-run semantics |
| `.claude/settings.json` | 222 | Claude Code project settings (model pin, hooks, permissions) |
| `.claude/settings.local.json` | 27 | Claude Code machine-local settings overrides |

## .claude/agents/ (4 files)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/agents/eos-code-reviewer.md` | 46 | You are a senior staff engineer doing adversarial code review on the EOS codebase. |
| `.claude/agents/eos-researcher.md` | 33 | You are the EOS Research Agent. |
| `.claude/agents/eos-simplifier.md` | 34 | You are the EOS Simplifier. |
| `.claude/agents/eos-verifier.md` | 35 | You are the EOS Verification Agent. |

## .claude/commands/ (24 files)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/commands/babysit.md` | 29 | Running babysit check. |
| `.claude/commands/browser-task.md` | 36 | Run a browser task using Playwright. |
| `.claude/commands/commit-push-pr.md` | 23 | Commit, push, and open a PR. |
| `.claude/commands/constraint-check.md` | 53 | Run a constraint check across all ventures. |
| `.claude/commands/council.md` | 36 | Council Mode — Multi-Agent Problem Solving |
| `.claude/commands/deploy.md` | 12 | Deploy changes to running services. |
| `.claude/commands/eod-sync.md` | 60 | Run end of day sync for Antony. Write to Notion and return the link. |
| `.claude/commands/eos-audit.md` | 68 | Run a full EOS system audit and report what's working, what's broken, and what's missing. |
| `.claude/commands/eos-build.md` | 52 | Claude Code slash command — eos build |
| `.claude/commands/eos-deploy.md` | 54 | Claude Code slash command — eos deploy |
| `.claude/commands/eos-fix.md` | 52 | Read the broken module, diagnose the root cause, fix it, test it, confirm it imports clean. |
| `.claude/commands/eos-sync.md` | 55 | Claude Code slash command — eos sync |
| `.claude/commands/morning-brief.md` | 69 | Generate a morning brief for Antony. Write it to Notion and return the link. |
| `.claude/commands/primitive-check.md` | 21 | Check primitive validity for current stage. |
| `.claude/commands/run-outreach.md` | 36 | Run outreach operations. |
| `.claude/commands/session-start.md` | 11 | Load full EOS context at start of session. |
| `.claude/commands/start-loops.md` | 44 | Starting EOS autonomous loops for this session. |
| `.claude/commands/status.md` | 13 | Check full EOS system status. |
| `.claude/commands/test-agent.md` | 20 | Test a specific EOS agent end-to-end. |
| `.claude/commands/test-all-agents.md` | 20 | Test all 4 EOS agents end-to-end. |
| `.claude/commands/test-all.md` | 9 | Run Core Test Suite |
| `.claude/commands/update-skills.md` | 27 | python3 -c " |
| `.claude/commands/use-opusplan.md` | 14 | Switching to opusplan for this session. |
| `.claude/commands/voice-debug.md` | 24 | Debug the Discord voice pipeline. |

## .claude/hooks/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/hooks/validate_change.py` | 114 | Pre-tool-use hook for EntrepreneurOS Claude Code sessions. |

## .claude/rules/ (13 files)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/rules/agents.md` | 29 | Agent Rules for EOS |
| `.claude/rules/architecture-layers.md` | 41 | Architecture Layer Law |
| `.claude/rules/browser-verification.md` | 50 | Browser Verification Law (NON-NEGOTIABLE) |
| `.claude/rules/client-failure-observability.md` | 62 | Client-Failure Observability Law (NON-NEGOTIABLE) |
| `.claude/rules/credential-injection.md` | 26 | Credential Injection Law (NON-NEGOTIABLE — ENFORCED BY PRE-COMMIT) |
| `.claude/rules/device-naming.md` | 18 | Device Naming Protocol |
| `.claude/rules/instance-context.md` | 22 | Instance Context Law |
| `.claude/rules/ontology-layers.md` | 87 | Ontology / Metamodel Layer Law |
| `.claude/rules/projection-boundary.md` | 27 | Projection Boundary Law |
| `.claude/rules/projection-read-surfaces.md` | 99 | Projection Read-Surface Discipline |
| `.claude/rules/python.md` | 18 | Python Rules for EOS |
| `.claude/rules/skills.md` | 26 | Skills Rules for EOS |
| `.claude/rules/type-coherence.md` | 34 | Type Coherence Law |

## .claude/skills/ (110 files)

| Path | Lines | Purpose |
|---|---|---|
| `.claude/skills/brandkit` | — | symlink → `../../.agents/skills/brandkit` |
| `.claude/skills/browser-control.md` | 84 | Browser Control — Best Practices |
| `.claude/skills/claude-code-cli.md` | 116 | Claude Code CLI — Best Practices |
| `.claude/skills/debug-agent.md` | 47 | How to Debug an EOS Agent |
| `.claude/skills/deploy-service.md` | 42 | How to Deploy EOS Service Changes |
| `.claude/skills/design-taste-frontend` | — | symlink → `../../.agents/skills/design-taste-frontend` |
| `.claude/skills/design-taste-frontend-v1` | — | symlink → `../../.agents/skills/design-taste-frontend-v1` |
| `.claude/skills/discord-admin.md` | 171 | Discord Admin — Best Practices |
| `.claude/skills/full-output-enforcement` | — | symlink → `../../.agents/skills/full-output-enforcement` |
| `.claude/skills/gpt-taste` | — | symlink → `../../.agents/skills/gpt-taste` |
| `.claude/skills/groq-api.md` | 70 | Groq API — Best Practices |
| `.claude/skills/high-end-visual-design` | — | symlink → `../../.agents/skills/high-end-visual-design` |
| `.claude/skills/humanizer` | — | symlink → `../../.agents/skills/humanizer` |
| `.claude/skills/image-to-code` | — | symlink → `../../.agents/skills/image-to-code` |
| `.claude/skills/imagegen-frontend-mobile` | — | symlink → `../../.agents/skills/imagegen-frontend-mobile` |
| `.claude/skills/imagegen-frontend-web` | — | symlink → `../../.agents/skills/imagegen-frontend-web` |
| `.claude/skills/impeccable/SKILL.md` | 168 | — |
| `.claude/skills/impeccable/reference/adapt.md` | 311 | > **Additional context needed**: target platforms/devices and usage contexts. |
| `.claude/skills/impeccable/reference/animate.md` | 201 | > **Additional context needed**: performance constraints. |
| `.claude/skills/impeccable/reference/audit.md` | 133 | skill reference doc — audit |
| `.claude/skills/impeccable/reference/bolder.md` | 113 | skill reference doc — bolder |
| `.claude/skills/impeccable/reference/brand.md` | 108 | Brand register |
| `.claude/skills/impeccable/reference/clarify.md` | 288 | > **Additional context needed**: audience technical level and users' mental state in context. |
| `.claude/skills/impeccable/reference/codex.md` | 105 | Codex: Visual Direction & Asset Production |
| `.claude/skills/impeccable/reference/colorize.md` | 257 | > **Additional context needed**: existing brand colors. |
| `.claude/skills/impeccable/reference/craft.md` | 123 | Craft Flow |
| `.claude/skills/impeccable/reference/critique.md` | 767 | ### Purpose |
| `.claude/skills/impeccable/reference/delight.md` | 302 | > **Additional context needed**: what's appropriate for the domain (playful vs professional vs quirky vs elegant). |
| `.claude/skills/impeccable/reference/distill.md` | 111 | skill reference doc — distill |
| `.claude/skills/impeccable/reference/document.md` | 429 | skill reference doc — document |
| `.claude/skills/impeccable/reference/extract.md` | 69 | Extract Flow |
| `.claude/skills/impeccable/reference/harden.md` | 347 | skill reference doc — harden |
| `.claude/skills/impeccable/reference/hooks.md` | 90 | /impeccable hooks |
| `.claude/skills/impeccable/reference/init.md` | 172 | Init Flow |
| `.claude/skills/impeccable/reference/interaction-design.md` | 189 | Interaction Design |
| `.claude/skills/impeccable/reference/layout.md` | 161 | skill reference doc — layout |
| `.claude/skills/impeccable/reference/live.md` | 718 | skill reference doc — live |
| `.claude/skills/impeccable/reference/onboard.md` | 234 | > **Additional context needed**: the "aha moment" you want users to reach, and users' experience level. |
| `.claude/skills/impeccable/reference/optimize.md` | 258 | skill reference doc — optimize |
| `.claude/skills/impeccable/reference/overdrive.md` | 130 | Start your response with: |
| `.claude/skills/impeccable/reference/polish.md` | 241 | > **Additional context needed**: quality bar (MVP vs flagship). |
| `.claude/skills/impeccable/reference/product.md` | 60 | Product register |
| `.claude/skills/impeccable/reference/quieter.md` | 99 | skill reference doc — quieter |
| `.claude/skills/impeccable/reference/shape.md` | 165 | skill reference doc — shape |
| `.claude/skills/impeccable/reference/typeset.md` | 279 | skill reference doc — typeset |
| `.claude/skills/impeccable/scripts/command-metadata.json` | 94 | skill support script — command metadata |
| `.claude/skills/impeccable/scripts/context-signals.mjs` | 225 | Context-signals gatherer for the bare `{{command_prefix}}impeccable` |
| `.claude/skills/impeccable/scripts/context.mjs` | 961 | Context loader: prints PRODUCT.md (and DESIGN.md if present) as one |
| `.claude/skills/impeccable/scripts/critique-storage.mjs` | 242 | Critique persistence helper. |
| `.claude/skills/impeccable/scripts/detect-csp.mjs` | 198 | Scan a project tree for Content-Security-Policy signals and classify the |
| `.claude/skills/impeccable/scripts/detect.mjs` | 21 | skill support script — detect |
| `.claude/skills/impeccable/scripts/detector/browser/injected/index.mjs` | 1,937 | skill support script — index |
| `.claude/skills/impeccable/scripts/detector/cli/main.mjs` | 290 | skill support script — main |
| `.claude/skills/impeccable/scripts/detector/design-system.mjs` | 750 | skill support script — design system |
| `.claude/skills/impeccable/scripts/detector/detect-antipatterns-browser.js` | 5,138 | Anti-Pattern Browser Detector for Impeccable |
| `.claude/skills/impeccable/scripts/detector/detect-antipatterns.mjs` | 50 | Anti-Pattern Detector for Impeccable |
| `.claude/skills/impeccable/scripts/detector/engines/browser/detect-url.mjs` | 277 | skill support script — detect url |
| `.claude/skills/impeccable/scripts/detector/engines/regex/detect-text.mjs` | 568 | skill support script — detect text |
| `.claude/skills/impeccable/scripts/detector/engines/static-html/css-cascade.mjs` | 1,015 | skill support script — css cascade |
| `.claude/skills/impeccable/scripts/detector/engines/static-html/detect-html.mjs` | 234 | skill support script — detect html |
| `.claude/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs` | 189 | skill support script — screenshot contrast |
| `.claude/skills/impeccable/scripts/detector/findings.mjs` | 12 | skill support script — findings |
| `.claude/skills/impeccable/scripts/detector/node/file-system.mjs` | 198 | skill support script — file system |
| `.claude/skills/impeccable/scripts/detector/profile/profiler.mjs` | 166 | skill support script — profiler |
| `.claude/skills/impeccable/scripts/detector/registry/antipatterns.mjs` | 448 | skill support script — antipatterns |
| `.claude/skills/impeccable/scripts/detector/rules/checks.mjs` | 2,671 | skill support script — checks |
| `.claude/skills/impeccable/scripts/detector/shared/color.mjs` | 124 | ─── Section 2: Color Utilities ───────────────────────────────────────────── |
| `.claude/skills/impeccable/scripts/detector/shared/constants.mjs` | 101 | ─── Section 1: Constants ─────────────────────────────────────────────────── |
| `.claude/skills/impeccable/scripts/detector/shared/inline-ignores.mjs` | 148 | Inline, in-file ignore directives — eslint-disable-style waivers that live at |
| `.claude/skills/impeccable/scripts/detector/shared/page.mjs` | 7 | Check if content looks like a full page (not a component/partial) |
| `.claude/skills/impeccable/scripts/hook-admin.mjs` | 661 | `/impeccable hooks <on\|off\|status\|reset>` — manage the design hook runtime |
| `.claude/skills/impeccable/scripts/hook-before-edit.mjs` | 476 | Impeccable design hook — Cursor preToolUse write gate. |
| `.claude/skills/impeccable/scripts/hook-lib.mjs` | 1,632 | Shared library for the Impeccable design hook. |
| `.claude/skills/impeccable/scripts/hook.mjs` | 61 | Impeccable design hook — PostToolUse entry point. |
| `.claude/skills/impeccable/scripts/lib/design-parser.mjs` | 842 | Parse a DESIGN.md (Stitch-spec format) into a structured JSON model that |
| `.claude/skills/impeccable/scripts/lib/impeccable-config.mjs` | 638 | CLI-side reader/writer for the unified `.impeccable` config. |
| `.claude/skills/impeccable/scripts/lib/impeccable-paths.mjs` | 128 | skill support script — impeccable paths |
| `.claude/skills/impeccable/scripts/lib/is-generated.mjs` | 69 | Decide whether a given file is "generated" (regenerated by a build step, |
| `.claude/skills/impeccable/scripts/lib/target-args.mjs` | 42 | skill support script — target args |
| `.claude/skills/impeccable/scripts/live-accept.mjs` | 812 | CLI helper: deterministic accept/discard of variant sessions. |
| `.claude/skills/impeccable/scripts/live-browser-dom.js` | 146 | Browser-side DOM helpers for Impeccable live mode. |
| `.claude/skills/impeccable/scripts/live-browser-session.js` | 123 | Browser-side durable session helpers for Impeccable live mode. |
| `.claude/skills/impeccable/scripts/live-browser.js` | 11,173 | Impeccable Live Variant Mode - Browser Script |
| `.claude/skills/impeccable/scripts/live-commit-manual-edits.mjs` | 1,241 | CLI helper: apply pending live copy edits as one AI-owned batch. |
| `.claude/skills/impeccable/scripts/live-complete.mjs` | 75 | Canonical durable completion acknowledgement for Impeccable live sessions. |
| `.claude/skills/impeccable/scripts/live-copy-edit-agent.mjs` | 683 | Applies staged live copy-edit batches by waking a local AI coding agent. |
| `.claude/skills/impeccable/scripts/live-discard-manual-edits.mjs` | 51 | CLI helper: discard pending manual edits from the buffer without applying. |
| `.claude/skills/impeccable/scripts/live-inject.mjs` | 583 | CLI helper: insert/remove the live variant mode script tag in the project's |
| `.claude/skills/impeccable/scripts/live-insert.mjs` | 272 | CLI helper: find an anchor element in source and splice an insert-variant |
| `.claude/skills/impeccable/scripts/live-manual-edit-evidence.mjs` | 363 | Collect evidence for pending live copy edits. |
| `.claude/skills/impeccable/scripts/live-poll.mjs` | 384 | CLI client for the live variant mode poll/reply protocol. |
| `.claude/skills/impeccable/scripts/live-resume.mjs` | 94 | Recover the next agent action from the durable live-session journal. |
| `.claude/skills/impeccable/scripts/live-server.mjs` | 1,135 | Live variant mode server (self-contained, zero dependencies). |
| `.claude/skills/impeccable/scripts/live-status.mjs` | 61 | Print durable recovery status for Impeccable live sessions. |
| `.claude/skills/impeccable/scripts/live-target.mjs` | 30 | skill support script — live target |
| `.claude/skills/impeccable/scripts/live-wrap.mjs` | 894 | CLI helper: find an element in source and wrap it in a variant container. |
| `.claude/skills/impeccable/scripts/live.mjs` | 297 | CLI entry point: prepare everything needed to enter the live variant poll loop. |
| `.claude/skills/impeccable/scripts/live/browser-script-parts.mjs` | 49 | skill support script — browser script parts |
| `.claude/skills/impeccable/scripts/live/completion.mjs` | 19 | skill support script — completion |
| `.claude/skills/impeccable/scripts/live/event-validation.mjs` | 137 | Shared event validation for the live helper server. |
| `.claude/skills/impeccable/scripts/live/insert-ui.mjs` | 458 | Pure helpers for live-mode insert UI (browser + tests). |
| `.claude/skills/impeccable/scripts/live/manual-apply.mjs` | 939 | skill support script — manual apply |
| `.claude/skills/impeccable/scripts/live/manual-edit-routes.mjs` | 357 | skill support script — manual edit routes |
| `.claude/skills/impeccable/scripts/live/manual-edits-buffer.mjs` | 152 | Shared helpers for the pending-manual-edits buffer on disk. |
| `.claude/skills/impeccable/scripts/live/session-store.mjs` | 289 | skill support script — session store |
| `.claude/skills/impeccable/scripts/live/svelte-component.mjs` | 826 | Svelte live-mode component injection helpers. |
| `.claude/skills/impeccable/scripts/live/sveltekit-adapter.mjs` | 274 | SvelteKit live-mode adapter. |
| `.claude/skills/impeccable/scripts/live/ui-core.mjs` | 180 | Framework-neutral Impeccable live chrome contract. |
| `.claude/skills/impeccable/scripts/live/vocabulary.mjs` | 36 | Canonical design-command vocabulary for Live Mode: each command's value, human |
| `.claude/skills/impeccable/scripts/modern-screenshot.umd.js` | 14 | skill support script — modern screenshot.umd |
| `.claude/skills/impeccable/scripts/palette.mjs` | 633 | Brand-seed picker. Returns one OKLCH seed color + the mood it most |
| `.claude/skills/impeccable/scripts/pin.mjs` | 214 | Pin/unpin sub-commands as standalone skill shortcuts. |
| `.claude/skills/improve` | — | symlink → `../../.agents/skills/improve` |
| `.claude/skills/industrial-brutalist-ui` | — | symlink → `../../.agents/skills/industrial-brutalist-ui` |
| `.claude/skills/instance-context-gate.md` | 75 | Instance Context Gate |
| `.claude/skills/karpathy-guidelines` | — | symlink → `../../.agents/skills/karpathy-guidelines` |
| `.claude/skills/last30days` | — | symlink → `../../.agents/skills/last30days` |
| `.claude/skills/material-list-builder.md` | 206 | Material List Builder |
| `.claude/skills/minimalist-ui` | — | symlink → `../../.agents/skills/minimalist-ui` |
| `.claude/skills/neon-db.md` | 104 | Neon PostgreSQL — Best Practices |
| `.claude/skills/new-agent.md` | 67 | How to Create a New EOS Agent |
| `.claude/skills/new-primitive.md` | 50 | How to Add a Business Primitive |
| `.claude/skills/new-skill.md` | 55 | How to Add a New Agent Skill |
| `.claude/skills/notion-api.md` | 135 | Notion API — Best Practices |
| `.claude/skills/redesign-existing-projects` | — | symlink → `../../.agents/skills/redesign-existing-projects` |
| `.claude/skills/refero-design` | — | symlink → `../../.agents/skills/refero-design` |
| `.claude/skills/stitch-design-taste` | — | symlink → `../../.agents/skills/stitch-design-taste` |
| `.claude/skills/verified-ui-testing.md` | 357 | Verified Software Testing Protocol |
