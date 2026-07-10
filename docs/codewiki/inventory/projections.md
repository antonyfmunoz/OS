---
type: codewiki-inventory
dir: projections
source_sha: a5f09e48e253dafdfcecee94a8e54f16224bae43
---

# `projections/` — File Inventory

**Files:** 69 regular + 0 symlinks · **Bytes:** 529,495

[Narrative page](../dirs/projections.md)


## projections/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `projections/__init__.py` | 1 | Application projections — scoped views of UMH capability. |

## projections/creatoros/ (9 files)

| Path | Lines | Purpose |
|---|---|---|
| `projections/creatoros/__init__.py` | 0 | package marker (empty) |
| `projections/creatoros/integration/__init__.py` | 1 | CreatorOS integration — creator platform, direct Postgres polling. |
| `projections/creatoros/integration/correlation.py` | 44 | Thread-safe in-memory correlation map for CreatorOS outcome writeback targeting. |
| `projections/creatoros/integration/handlers.py` | 150 | CreatorOS capability handler — implements CapabilityHandler Protocol. |
| `projections/creatoros/integration/manifest.py` | 139 | CreatorOS integration manifest — declares sockets, signals, capabilities, config. |
| `projections/creatoros/integration/outcomes.py` | 180 | CreatorOS outcome receiver — writes pipeline outcomes back to CreatorOS Postgres. |
| `projections/creatoros/integration/readiness.py` | 82 | CreatorOS projection activation / readiness — P4S-10. |
| `projections/creatoros/integration/signals.py` | 146 | CreatorOS signal emitter — builds SignalEnvelopes from polled CreatorOS database rows. |
| `projections/creatoros/integration/tables.py` | 439 | Typed query helpers for CreatorOS database tables. |

## projections/eos/ (50 files)

| Path | Lines | Purpose |
|---|---|---|
| `projections/eos/__init__.py` | 92 | EOS projection — EntrepreneurOS department agents registered on the substrate. |
| `projections/eos/agents/__init__.py` | 43 | EOS department agents — one per department in the ARCHITECTURE.md hierarchy. |
| `projections/eos/agents/base.py` | 198 | Base department agent with skill execution, permission tiers, and governance integration. |
| `projections/eos/agents/ceo.py` | 212 | EOS CEO Agent — strategic decision making for entrepreneur operations. |
| `projections/eos/agents/customer_success.py` | 283 | EOS Customer Success Agent — retention, satisfaction, support routing. |
| `projections/eos/agents/engineering.py` | 219 | EOS Engineering Agent — technical execution, architecture, deployment. |
| `projections/eos/agents/finance.py` | 236 | EOS Finance Agent — revenue tracking, expense management, financial forecasting. |
| `projections/eos/agents/hr.py` | 207 | EOS HR Agent — hiring pipeline, team management, onboarding. |
| `projections/eos/agents/legal.py` | 269 | EOS Legal Agent — contract review, compliance tracking, entity management. |
| `projections/eos/agents/marketing.py` | 213 | EOS Marketing Agent — content strategy and brand execution. |
| `projections/eos/agents/operations.py` | 243 | EOS Operations Agent — workflow optimization, process automation, system health. |
| `projections/eos/agents/product.py` | 246 | EOS Product Agent — roadmap management, feature prioritization, user feedback. |
| `projections/eos/agents/sales.py` | 169 | EOS Sales Agent — pipeline management and outreach execution. |
| `projections/eos/entities.py` | 877 | EOS entity definitions — full entity hierarchy. |
| `projections/eos/integration/DESIGN.md` | 1,463 | EOS Integration — Design Report |
| `projections/eos/integration/__init__.py` | 1 | EOS (EntrepreneurOS) integration — direct Postgres polling, multi-org. |
| `projections/eos/integration/action_decisions.py` | 293 | EOS ActionProposal approval-command seam — WP-P4-EOS-ACTION-APPROVAL-COMMAND-001. |
| `projections/eos/integration/action_execution.py` | 344 | EOS approved-action executor seam — WP-P4-EOS-EXECUTOR-ACTIVATE-001. |
| `projections/eos/integration/action_proposals.py` | 247 | EOS ActionProposal read seam — WP-P4-EOS-ACTION-PROPOSAL-READ-001. |
| `projections/eos/integration/action_seam.py` | 132 | EOS action-executor seam map — WP-P4-EOS-ACTION-EXECUTOR-SEAM-001. |
| `projections/eos/integration/correlation.py` | 41 | Thread-safe in-memory correlation map for EOS outcome writeback targeting. |
| `projections/eos/integration/handlers.py` | 157 | EOS capability handler — implements CapabilityHandler Protocol. |
| `projections/eos/integration/manifest.py` | 156 | EOS integration manifest — declares sockets, signals, capabilities, config. |
| `projections/eos/integration/module_map.py` | 117 | EOS app-body module map — WP-P4-EOS-APP-MODULE-MAP-001. |
| `projections/eos/integration/outcomes.py` | 182 | EOS outcome receiver — writes pipeline outcomes back to EOS Postgres. |
| `projections/eos/integration/poller.py` | 256 | EOS poller — background thread that polls EOS Postgres tables for new rows. |
| `projections/eos/integration/readiness.py` | 119 | EOS projection activation / readiness — WP-P4-006. |
| `projections/eos/integration/signals.py` | 157 | EOS signal emitter — builds SignalEnvelopes from polled EOS database rows. |
| `projections/eos/integration/tables.py` | 1,024 | Typed query helpers for EOS database tables. |
| `projections/eos/integration/tasks_read.py` | 103 | EOS `/eos/tasks` read surface — P4S-20 (governed-effect visibility). |
| `projections/eos/views/__init__.py` | 7 | EOS views — project substrate data into entrepreneur-facing dashboards. |
| `projections/eos/views/activity.py` | 91 | Activity view — projects recent system activity into a founder-facing feed. |
| `projections/eos/views/kpis.py` | 145 | KPI view — projects business metrics into founder-facing KPI cards. |
| `projections/eos/views/pipeline.py` | 101 | Pipeline view — projects CRM/sales data into a founder-facing pipeline. |
| `projections/eos/workflows/__init__.py` | 37 | EOS workflows — automated sequences triggered by signals. |
| `projections/eos/workflows/browser.py` | 309 | Browser workflow — governed web scraping and research. |
| `projections/eos/workflows/content.py` | 143 | Content calendar workflow — schedule and track content across channels. |
| `projections/eos/workflows/daily.py` | 240 | Daily rhythm workflow — governed morning brief and end-of-day. |
| `projections/eos/workflows/design.py` | 311 | Design workflow — governed design asset management. |
| `projections/eos/workflows/document.py` | 316 | Document generation workflow — governed document creation. |
| `projections/eos/workflows/execution.py` | 196 | Execution workflow — governed task lifecycle tracking. |
| `projections/eos/workflows/followup.py` | 139 | Follow-up workflow — automated follow-up on stale conversations. |
| `projections/eos/workflows/github.py` | 156 | GitHub workflow — governed PR and branch operations. |
| `projections/eos/workflows/outreach.py` | 162 | Outreach workflow — automated prospect outreach sequence. |
| `projections/eos/workflows/planning.py` | 257 | Planning workflow — governed strategic planning with outcome tracking. |
| `projections/eos/workflows/research.py` | 243 | Research workflow — governed research with outcome tracking. |
| `projections/eos/workflows/review.py` | 317 | Review workflow — governed code/work review with outcome tracking. |
| `projections/eos/workflows/runner.py` | 202 | WorkflowRunner — executes multi-step workflows through governed mutation. |
| `projections/eos/workflows/slack.py` | 187 | Slack workflow — governed messaging with outbox-based delivery. |
| `projections/eos/workflows/types.py` | 81 | Workflow types — shared data structures for all EOS workflows. |

## projections/lyfeos/ (9 files)

| Path | Lines | Purpose |
|---|---|---|
| `projections/lyfeos/__init__.py` | 0 | package marker (empty) |
| `projections/lyfeos/integration/__init__.py` | 1 | LyfeOS integration — life optimization platform, direct Postgres polling. |
| `projections/lyfeos/integration/correlation.py` | 41 | Thread-safe in-memory correlation map for LyfeOS outcome writeback targeting. |
| `projections/lyfeos/integration/handlers.py` | 151 | LyfeOS capability handler — implements CapabilityHandler Protocol. |
| `projections/lyfeos/integration/manifest.py` | 142 | LyfeOS integration manifest — declares sockets, signals, capabilities, config. |
| `projections/lyfeos/integration/outcomes.py` | 180 | LyfeOS outcome receiver — writes pipeline outcomes back to LyfeOS Postgres. |
| `projections/lyfeos/integration/readiness.py` | 79 | LyfeOS projection activation / readiness — P4S-10. |
| `projections/lyfeos/integration/signals.py` | 166 | LyfeOS signal emitter — builds SignalEnvelopes from polled LyfeOS database rows. |
| `projections/lyfeos/integration/tables.py` | 503 | Typed query helpers for LyfeOS database tables. |
