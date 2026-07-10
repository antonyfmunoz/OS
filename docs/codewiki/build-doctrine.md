---
type: codewiki-page
dir: (cross-cutting)
---

# Build Doctrine + Verified Gap Map — 2026-07-10

How a first-principles team would run this project, plus the complete
code-verified gap architecture. Produced by a six-lens principal-engineer
completeness panel (distributed-systems/SRE, security/adversarial-ML,
ML/LLM-ops, data/persistence, product/UX, org/economics/legal) with every
claim grep-or-read-verified against the tree at `main` (2026-07-10).
Companion pages: [vision-alignment.md](vision-alignment.md) ·
[canonical-registry.md](canonical-registry.md) ·
[audit-2026-07-10.md](audit-2026-07-10.md).

## The doctrine

1. **One wall metric:** T(intent → verified change in reality) × trust.
   Not instrumented today; instrument first.
2. **The algorithm, in order:** make requirements less dumb → **delete** →
   simplify → accelerate → automate. Deletions are already approved in the
   findings register (saas/, .claire/, 32GB archive, dual trace stores,
   duplicate council, three obsolete roadmap numberings).
3. **The factory is the product:** hours invested in evals/gates/golden
   traces compound; hand-built features don't. The audit→wiki→gap-map
   pipeline of this session IS the factory — make it the heartbeat.
4. **Org chart for one human + a fleet:** founder = intent and approvals
   only; fleet = execution; gates + evals = management. Every capability has
   an owning gate and an eval, or it doesn't ship. Weekly hard gate on the
   wall metric + findings register. Test-green ≠ product-green.
5. **Idiot-index:** cost of a governed task ÷ raw inference cost, per task
   class. Unknown today (cost logged, never attributed); measure it.

## Tier 0 — Silent-breach primitives (NOW)

| Gap | Verified reality | Fix |
|---|---|---|
| RLS tenant firewall is a no-op | `db.py` sets `app.current_org_id` but ZERO `CREATE POLICY`/`ENABLE ROW LEVEL SECURITY` exists anywhere | Real per-table policies + CI gate |
| Traces mutable | `trace.py` persists `ON CONFLICT DO UPDATE` | Hash-chain + append-only grants |
| Tool-output injection undefended | Grounding firewall is anti-hallucination only; browser/scraper text reaches planning as trusted | Untrusted-content boundary at perception |
| Generated code unsandboxed | Regex deny-list only; code comments admit "OS-level sandboxing future phase" | bubblewrap/gVisor per-task, no-net default |
| Approvals die silently | Discord buttons expire at 120s, no re-delivery/escalation/SLA (`approval_bridge.py:21,47`) | Approval SLA + escalation + re-delivery |
| Misc NOW | VNC `-nopw`; no emergency credential revocation; no threat-model doc | Password/bind; revoke path; docs/security/threat-model.md |

## Tier 1 — The flywheel isn't wired (moat = claim, not mechanism)

Verified: `training_extractor.py` + `finetune_harness.py` have **zero
production callers**; approval intercepts capture approve/reject + reason but
**never link the decision to the originating trace** — the scarcest label is
generated and discarded every run; **no preference-capture UI** (RLHF endpoint
exists, nothing calls it from the renderer); two divergent trace stores
(append-only JSONL vs mutable Postgres); no eval harness; no prompt registry
(prompts are inline literals — the least-governed artifact in a
"skeleton-governs" system); no token-budget accounting (only per-call
`max_tokens`); confidence stored but never calibrated; `PROVIDER_QUALITY` is a
hand-typed constant nothing updates and routing never self-tunes; no
model-behavior drift detection; malformed LLM JSON silently discarded (no
central structured_call parse-repair-retry); retrieval quality of the
memory/knowledge stack unmeasured (the 311-commit-stale graph went undetected
for exactly this reason); `execution_economy.py` has the right
cost/latency/quality ledger model but **`.record()` is never called from the
live path** — economics modeled, never measured.

**Impossible to backfill — start capturing NOW even if unused:** (a)
**consent/data-rights fields on every trace** (license class, PII status,
usage rights) — without them the corpus is legally untrainable the moment a
second party's data enters it; (b) **provenance metadata on training rows**;
(c) cost attribution per task class. Retroactive consent does not exist.

Fix order: eval harness + prompt registry → unified event journal →
approval↔trace linkage + preference capture UI → consent/provenance schema →
economy wiring → calibration → drift detection.

## Tier 2 — Distributed-spine + data-layer hardening (before elastic parallelism)

Spine: no DB migrations (lazy `CREATE TABLE IF NOT EXISTS` across ~12
modules, no `schema_version` — the frozen PLATFORM_SPEC demands a migration
process that has no machinery); no distributed leases/leader election
(Postgres advisory-lock lease needed — multiple loops already mutate shared
state; two orchestrators during a restart = split-brain); **lost-update bug
live today**: `entity_store.py` has a `version` column that is never checked
— blind last-writer-wins upserts under concurrent loops; no logical clock
(journals ordered by wall-clock `time.time()` across VPS/Beast/Fly — skew
reorders/drops events at query boundaries); mesh dispatch has **no
ack/redelivery-dedup** (a Tailscale blip re-executes a dispatched WorkPacket
— double purchase/email); no SIGTERM drain in `operator_api` lifespan (every
live-edit restart can kill an executor between state-write and
trace-persist); no saturation SLOs (queue depth/backlog age unmeasured —
latency reads green while backlog grows unbounded); no config-drift gate
(staged systemd/env vs live — the mode that shipped `UMH_DEV_BYPASS=true`);
cost metered but never enforced — **no spend ceiling exists**: a fallback
cascade to paid APIs runs unbounded (the dollar analog of the CPU-gate
incident); no per-tenant quotas.

Data layer: **no schema registry / versioned event envelope** — 82 distinct
JSONL shapes + 24 tables carry zero `schema_version`; the first shape change
makes historical trajectories silently unparseable; **journal appends are
non-atomic** — bare `open("a").write`, no fsync/lock/temp-rename, multiple
host processes appending concurrently can interleave into poisoned lines;
9 colliding JSONL basenames with different shapes; journal "rotation"
overwrites the single `.jsonl.old`; no ANN index on embeddings (brute-force
scan; retrieval degrades linearly with corpus growth); no embedding reindex
lifecycle on model change (mixed-model cosine = silent garbage neighbors);
no declared system-of-record between Neon and the file journals; no
markdown/vault↔DB sync contract; Neon has **zero backup** (`backup.sh` tars
local files only, never restores-tests); no time-series metrics store; no
org-scoped erasure across 24 tables + 82 JSONL files.

## Tier 3 — Productization gate (before design partner #1)

Runtime tenancy absent — org bound **once at process boot** from env var
(`context.py:37`), and **`governed_mutation()` itself takes no org/tenant
argument** — the admission controller is tenant-blind; provisioning
automation broken (`install.sh` literal `[repo]` URL; `setup.sh` imports
nonexistent `runtime.setup_wizard`);
billing-grade per-tenant/per-outcome metering absent (day×subsystem JSON
only); graduated autonomy loop absent (authority is static policy; nothing
consumes track record); single notification choke point absent (channels ping
independently; presence engine's interrupt logic unwired); remote diagnostics
bundle absent; cockpit first-run/progressive disclosure absent (80 panels,
no tour); purpose-built mobile approval surface absent; per-trace
"why did it do that" explanation view absent.

## Tier 4 — Moat protection (before proprietary models)

Skill/capability package signing + provenance (97 executable skills,
nothing verifies integrity); corpus-poisoning defense + provenance metadata
(capture NOW or early corpus unusable); adversarial eval suite + red-team
cadence; model-extraction guardrails at operator surfaces; PII
classification + `purge_tenant()` erasure across memory/traces/corpus;
per-agent behavioral velocity governor + quarantine (agents can loop
unbounded within a risk tier today); verdict-token replay protection
(nonce/jti) and per-issuer keys.

## Tier 5 — Org/legal/economic scaffolding

Threat model; IR runbooks + security-event stream; **Anthropic
ToS/subscription continuity policy** — cc_sdk detects 429s but has no quota
forecast or ToS guard, and silently falls through to *paid* APIs, inverting
the $0 economics with no policy deciding; vendor-concentration register +
per-vendor failure runbooks (Anthropic/Fly/Neon/Hostinger/Tailscale/1Password
— any one halts the organism); **hard spend-ceiling gate** (sibling to
cpu_gate, consulted by model_router); **ADR discipline** (docs/adr/ immutable
records + gate requiring ADR link on Law/PLATFORM_SPEC changes — the
canon-rot items ARE ADR-discipline failures); **DORA/change-failure telemetry
for the fleet** (agents deploy; nothing measures their change-failure rate or
MTTR); **agency-law gate** — no machine-enforced "no agent may create a
binding obligation/e-sign/transact without human ratification" (the legal
agent is an EOS advisor, not a boundary); **skill license framework** — zero
LICENSE files, no SPDX field in any SKILL.md, 15+ vendored packages with
untracked upstream licenses, no root LICENSE decision; retention/DPA
machinery (no TTLs, no tenant-delete cascade, no DPA template); **CODEOWNERS
for agents** + review-escalation rules (the two-executors-corrupted-main
incident is this gap); **EU AI Act classification** (an autonomous execution
system heading to physical actuation is high-risk scope; trace+governance
artifacts are most of the conformity evidence — classify now to shape
design); signed authorization envelopes (non-repudiation of "human X
approved action Y"); deliberate open-vs-proprietary decision + vendored
license audit before any external distribution.

## Re-sequenced program

Stage 0′ = Tier 0 (days). Stage 1 (kernel boundary) += event-journal
unification + trace immutability. Stage 3 (evals before learning) absorbs
Tier 1; preference capture starts immediately (corpus accrues forward only).
Stage 4.5 (parallel dispatcher) requires Tier 2. Stage 6 (OS-ification)
gated on Tier 3. Stage 7 (proprietary intelligence) gated on Tier 4.
Tier 5 runs continuously.

## Coverage statement

Six lenses ran to completion with full ranked lists (security 18, product 12,
data 14, ML-ops 12, distributed-systems 12, org/economics/legal 14 — ~82
items) plus four independent code-verification bundles; every claim
grep-or-read-verified at `a5f09e48e`/`c806e75e2`. Four items are flagged
**impossible to backfill** and must precede any second tenant: tenant scope
in `governed_mutation` + real RLS policies; consent/data-rights fields on
traces; provenance metadata on training rows; cost attribution on the
governed path. Remaining unknown-unknowns concentrate at two unreached
frontiers — model-training operations and physical actuation. Re-run this
completeness loop at each of those gates: 100% is a property of a moment.

## See also

[vision-alignment.md](vision-alignment.md) ·
[canonical-registry.md](canonical-registry.md) ·
[health-findings.md](health-findings.md) ·
[conventions.md](conventions.md)
