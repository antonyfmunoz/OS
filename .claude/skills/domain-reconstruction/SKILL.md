---
name: domain-reconstruction
description: Use when asked to reconstruct a domain into a grounded world model, build the grounded self-model, produce a territory map, or run the blind-witness / adversarial-counsel harness on a topic. Also when asked to inspect or interpret a prior reconstruction run.
trigger: conversational
effort: high
context: fork
allowed-tools: Bash, Read, Grep, WebSearch, WebFetch
---

# Domain Reconstruction

Normative source of truth: **DOMAIN_RECONSTRUCTION_SPEC.md** (repo root, v0.3.0 DRAFT).
This skill is the operator procedure; the spec is the law. When they disagree, the
spec wins and this file is wrong — fix it.

Governing invariant (spec §4.3): a desired state, design proposal, roadmap item, or
documented claim is a **claim**, never an **observation that the thing exists**.
Everything below enforces that one line.

## What you are building

A reconstruction is an evidence-grounded, provenance-carrying, falsifiable model of
a bounded slice of reality — descriptive / epistemic / mechanistic /
predictive-control records over the 20-concept kernel (spec §4.2, §4.4). Two entry
modes:

- **Grounded self-model** — reconstruct UMH's own runtime (the v1 slice). Code path.
- **Territory-map / witness-counsel harness** — reconstruct an external topic as a
  calibrated report. OPTIONAL acquisition method (spec §4.13). Report path, no code.

## Build the grounded self-model

```
python3 scripts/verify_grounded_self_model.py --build
```

- Output is **run-scoped**: `data/world_models/self/runs/<run_id>/`. Never write a
  self-model outside a run dir; never overwrite a prior run (append-preserving,
  spec §4.6).
- The builder composes existing runtimes — it replaces none of them: `SelfModel`
  (`substrate/self_model.py`), `extract_world_model()`
  (`substrate/organism/world_model.py`), `ContradictionEngine`
  (`substrate/organism/contradiction_engine.py`), `RealityGraph`
  (`substrate/organism/reality_graph.py`), `RealityIntelligenceEngine`
  (`substrate/reality_model/reality_intelligence.py`), `PredictiveSelfModel`
  (`substrate/organism/self_model_predictor.py`).
- v1 integration boundary (spec §4.14): the builder writes NOTHING to canonical
  reality, registers no mutation, and does not touch `UMH_CANONICAL_RUNTIME_ROUTING`.
  If a build tries to call `governed_mutation()` or `CanonicalRealityWritePath`, stop
  — that is out of the v1 slice.

## Test evidence (v1.2)

```
python3 scripts/verify_grounded_self_model.py --run-tests reconstruction-spine-v1
```

Runs the bounded pytest selection with the evidence plugin and builds a run
ingesting the artifact (run copy: `test_report.json`). Truth hierarchy is never
collapsed: executed != passed != component-exercised != correct. Two outcome
dimensions per test (semantic_outcome + session_effect) with setup/call/
teardown phases preserved; classification comes from REGISTERED markers only
(`integration` — everything else is `unknown`). With no coverage tooling
installed, ZERO components gain a tested facet and CQ5 reports
PARTIALLY_ANSWERED with `component_mapping_status:
coverage_tooling_not_installed` — that is the honest result, not a defect. A
stale/dirty/plugin-error artifact is REJECTED, never ingested as valid.

Gotcha: the spine selection exercises the REAL canonical mutation path, so the
tests append to tracked `data/umh/**` runtime journals during the run. The CLI
detects post-run drift: non-`data/` drift FAILS acquisition (implementation
changed under the artifact); `data/`-only drift on a clean preflight is
restored automatically (side effects, not code change). `unit_tested` is
structurally unreachable here — no `unit` marker is registered.

## Inspect a run

Read the artifacts in this order (cheapest, highest-signal first):

1. `runs/<run_id>/manifest.json` — what was built, code/model version, run_id, timestamps.
2. `runs/<run_id>/acceptance.json` — the final status (see below) and per-check results.
3. `runs/<run_id>/convergence.md` — the human-readable reconstruction: maturity
   vectors, contradictions, recorded omissions.
4. `runs/<run_id>/claims.jsonl` — the AUTHORITATIVE claim ledger (model.json holds
   only indexes + the ledger hash). Beliefs are projections derived from it, never
   independently authored. This is where you audit the §4.3 invariant.

## Interpret unknowns and status

**Unknown is a valid, first-class result. Fabrication is failure.** An `unresolved`
identity or an unexpanded region recorded as a gap (spec §4.8, §4.10) is a correct
model, not an incomplete one.

The ONLY permitted final statuses (spec §4.12):

```
OPERATIONAL · PARTIALLY_OPERATIONAL · INSUFFICIENT_EVIDENCE · FAILED
```

`COMPLETE` is banned. `N/A` is never a pass — it drops out of the denominator, it
does not count green. A component with config but no observed running process is
PARTIALLY_OPERATIONAL with the missing facets named, never OPERATIONAL (spec §4.7
worked example).

## Witness / counsel harness (OPTIONAL acquisition method — spec §4.13)

Report-only. Produces a calibrated territory map, not a code artifact. Procedure:

1. **Lens generation** — enumerate the framings/angles the topic could be seen from.
2. **Blind witnesses** — gather independent observations per lens WITHOUT shared
   framing between witnesses.
3. **Adversarial counsels** — have critics argue opposing positions. Counsels must
   NOT see witness drafts mid-run (keeps critique independent).
4. **Deflation pass** — MANDATORY before trusting anything. Strip inflated,
   repeated, and unsourced claims; demote over-promoted causal statements.
5. **Calibrated synthesis** — assign each surviving claim a band:
   `FORCED (>0.90) · HIGH (0.75–0.90) · MODERATE (0.45–0.75) · BET (<0.45)`.
6. **Mythology graveyard** — list the claims that are definitively false.
7. **Ranked omissions** — record the map's own blind spots, ranked (spec §4.10).

Exemplars to imitate for section grammar (evidence preamble → bands → graveyard →
deflation corrections → omissions): the `data/reports/2026-07-18_*-territory-map.md`
corpus (10 maps, e.g. `data/reports/2026-07-18_sales-territory-map.md`). The
in-substrate adjudication precedent is `DeliberationCouncil`
(`substrate/understanding/deliberation/council.py`).

## Gotchas (real failure modes)

- **Blindness ≠ source independence.** Persona multiplication over one source is one
  source wearing many masks. Independence is measured by source LINEAGE (do the
  assertions trace to genuinely different sources), not by persona count. Do not let
  N witnesses over one article raise confidence (spec §4.13).
- **Never store a proposed design / roadmap / spec claim as an observation that the
  thing exists** (§4.3). A Docker service block is `deployment_configured`, not
  `running`. This is the failure the whole subsystem exists to prevent.
- **Textual repetition never promotes a causal rung** (§4.9). Ten sources saying "X
  causes Y" stays rung 1 (reported statement) with ten citations — not an
  established causal relation. Promotion needs evidence of the higher rung's kind.
- **N/A is never a pass.** A skipped or inapplicable check is recorded as
  not-applicable and excluded from the denominator — scoring it green fakes coverage.
- **The deflation pass is mandatory.** A synthesis you did not deflate is untrusted.
  Do not band or ship claims that skipped step 4.
- **Counsel must never see witness drafts mid-run.** Leaking witness output into
  counsel collapses the adversarial independence the harness is buying.
- **WebSearch budget exhaustion → disclose, don't fake.** If the search budget runs
  out, say so in the evidence-quality preamble ("recall-only for lenses N–M") and
  band the affected claims down. Never present recalled-from-memory claims as though
  they were freshly sourced.

## Verification step (REQUIRED — do not report done without it)

- **If a model was built** (self-model path):
  ```
  python3 scripts/verify_grounded_self_model.py --verify
  ```
  Confirm the run's `acceptance.json` carries `final_status` as one of the four
  permitted values and that the `no_design_as_implementation` criterion is PASS —
  no "supported" claim rests on declaration-facet observations alone.

- **If report-only** (witness/counsel path): verify the report contains every
  required section — evidence-quality preamble, FORCED/HIGH/MODERATE/BET bands,
  mythology graveyard, deflation corrections, and ranked omissions. A map missing any
  of these is not done.
