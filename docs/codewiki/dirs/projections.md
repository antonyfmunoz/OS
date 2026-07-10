---
type: codewiki-dir
dir: projections
---

# `projections/` — applications built ON the UMH substrate

**69 files · 529,495 bytes · [Full file inventory](../inventory/projections.md)**

## Purpose
`projections/` holds the **applications** that run on top of the universal
substrate. A projection is a scoped view of UMH capability for one product
domain: it registers agents, polls a product database, emits `SignalEnvelope`s
into the substrate spine, projects substrate state back into product-facing
views, and receives outcomes for writeback. Three projections live here —
**EOS** (EntrepreneurOS, the founder's operating company), **CreatorOS**, and
**LyfeOS** — but they are not peers in maturity: EOS is a full projection (49
files: department agents, views, workflows, a complete integration seam),
while CreatorOS and LyfeOS are **integration-only** (9 files each — signals,
handlers, outcomes, tables, readiness, manifest, correlation — no agents, no
views, no workflows).

## How it fits
Projections are the **top layer** of the four-layer dependency stack
(`projections/ → transports/ → adapters/ → substrate/`, per
[`.claude/rules/architecture-layers.md`](../../../.claude/rules/architecture-layers.md)).
Dependency direction is one-way downward: a projection may import from
`transports/`, `adapters/`, and `substrate/`, but **nothing imports upward into
`projections/`** as a hard rule. `projections/eos/__init__.py` states the
contract explicitly: it uses **only the public Substrate API**
(`substrate.execute`, `substrate.register`, `substrate.types`) — no internal
substrate imports.

Read paths flow the other way through transport wrappers:
`transports/api/cockpit_core_eos_routes.py`,
`transports/api/cockpit_entity_routes.py`, `transports/api/app.py`, and
`services/discord_bot_commands.py` reach into `projections/eos`. The one
grandfathered exception to the downward rule is
`substrate/integrations/product_connections.py`, a substrate-owned singleton
that reads EOS config — a sanctioned legacy `substrate → projections` import,
not a pattern to copy (see
[`.claude/rules/projection-read-surfaces.md`](../../../.claude/rules/projection-read-surfaces.md)).

The write path is legal for projections: `projections/eos/workflows/runner.py`
imports `transports.api.governed.governed_mutation` so every workflow step
passes through the one governed mutation contract.

## Structure

| Subdir | Files | Role |
|---|---|---|
| `eos/` | 50 (incl. `entities.py`, `integration/DESIGN.md`) | EntrepreneurOS — the full projection: department agents, founder views, governed workflows, Postgres integration seam |
| `eos/agents/` | 12 | One department agent per ARCHITECTURE.md department (CEO, sales, marketing, finance, engineering, HR, legal, operations, product, customer_success) over a shared `base.py` |
| `eos/views/` | 4 | Read-only projections of substrate state into founder dashboards (activity, KPIs, pipeline) |
| `eos/workflows/` | 16 | Automated signal-triggered sequences, all executed through `governed_mutation` via `runner.py` |
| `eos/integration/` | 15 | Postgres poller + signal emitter + capability handlers + outcome receiver + readiness read surface |
| `creatoros/integration/` | 9 | CreatorOS integration-only shell (no agents/views/workflows) |
| `lyfeos/integration/` | 9 | LyfeOS integration-only shell (no agents/views/workflows) |

## Key components

- **`eos/integration/readiness.py:42` — `eos_readiness()`** is the **reference
  projection read surface** (established by PR #171, WP-P4-006). It is the model
  every future read surface must follow per
  [`.claude/rules/projection-read-surfaces.md`](../../../.claude/rules/projection-read-surfaces.md):
  a single projection-owned accessor that composes existing substrate read
  surfaces, imports only downward, never raises, and returns a stable flat dict
  even when `EOS_DATABASE_URL` is unset. It is wired to the thin transport
  wrapper `GET /eos/activation` in `transports/api/cockpit_core_eos_routes.py`.
- **`eos/entities.py`** (877 lines) — the full EOS entity hierarchy. The
  largest single module in the directory.
- **`eos/integration/tables.py`** (1,024 lines) — typed query helpers for the
  EOS Postgres tables; `creatoros` (439) and `lyfeos` (503) have parallel
  `tables.py` files scoped to their own schemas.
- **`eos/integration/poller.py`** — the background thread that polls EOS
  Postgres for new rows and drives `signals.py` to build `SignalEnvelope`s.
- **`eos/workflows/runner.py`** — `WorkflowRunner`, the single entry point that
  runs every multi-step workflow through `governed_mutation`.
- **`eos/agents/base.py`** — the base department agent (skill execution,
  permission tiers, governance integration) that all 10 department agents
  extend.
- The **P4S / WP-P4-EOS action seam** — `action_proposals.py`,
  `action_decisions.py`, `action_execution.py`, `action_seam.py`,
  `tasks_read.py` — the governed-effect approval and visibility surface for
  proposed EOS actions.

## Data & state
- **Postgres (Neon, per-product)** — each projection's `integration/` polls its
  own product database via `load_<proj>_config()` reading a product
  `*_DATABASE_URL` env var (e.g. `EOS_DATABASE_URL`). When the env var is unset
  the projection reports `disconnected` and never raises.
- **`data/umh/projection_registry.json`** — the canonical projection seed. It
  registers `umh`, `eos`, `lyfeos`, and `cos` (CreatorOS) with `app_name`,
  `health_url`, `public_url`, and an `l4_workflow` verification target. It is
  read **only** through the substrate port
  (`substrate.sockets.projection_port.load_umh_projection_seed()`), never by
  opening the file directly.
- **Signals in / outcomes out** — `signals.py` emits `SignalEnvelope`s into the
  spine; `outcomes.py` writes pipeline outcomes back to the product Postgres;
  `correlation.py` keeps the thread-safe in-memory map that targets the
  writeback.

## Gotchas
- **EOS source truth is on the Beast, NOT here.** The full-stack EntrepreneurOS
  application (603 files, Clerk auth) is canonical on the Windows Beast node;
  `/opt/OS/projections/eos` may be a **mirror**. This is deliberate node-role
  discipline — the apps are kept separate so their source does not mix (memory:
  `project_projection_source_truth`, enforced by PR #173). `readiness.py`
  encodes this directly: it surfaces `beast_source_risk`, `beast_runtime_ready`,
  `mirror_fidelity`, `beast_head`, and `beast_probe_at` fields via
  `substrate.sockets.projection_port.get_beast_source_row()`. **Verify against
  the Beast before editing EOS application code here** — a local edit may be
  overwritten by the canonical source.
- **Projection Boundary Law** (`.claude/rules/projection-boundary.md`):
  projection-specific vocabulary (`EOS_ORG_ID`, `eos-*` names, `CreatorOS`,
  `LyfeOS`) must never leak into `substrate/`. Substrate exposes abstract ports;
  projections register at runtime through them. `check_projection_leak.py`
  enforces this pre-commit.
- **Read-surface discipline** (`.claude/rules/projection-read-surfaces.md`):
  only `/eos/activation` conforms today. `/eos/pipeline`, `/eos/kpis`,
  `/eos/activity`, `/eos/accountability`, `/eos/intelligence` are sanctioned
  legacy on a **shrink-only** allowlist — they build view objects inline. New
  `/eos/*` routes must conform to the `eos_readiness()` shape and are **not**
  added to the allowlist.
- **CreatorOS / LyfeOS are shells, not full products.** They have integration
  seams but no agents, views, or workflows. Do not assume feature parity with
  EOS from directory presence alone.
- The empty `creatoros/__init__.py` and `lyfeos/__init__.py` are package
  markers (0 lines) — the code lives under `integration/`.

## See also
- [`saas/`](saas.md) — the deleted TypeScript SaaS/edge bridge (superseded by
  the canonical Beast EOS)
- [`substrate/`](substrate.md) — the universal platform projections build on
- [`substrate/organism/`](substrate-organism.md) — the organism state layer
- [`transports/`](transports.md) — the I/O surfaces and governed write path
- [Architecture overview](../architecture.md)
- [Health findings](../health-findings.md)
