# P4-SYNC Campaign — UMH + Cockpit + EOS + LifeOS + CreatorOS

Compiled 2026-07-06 (Fable compile; Opus/Sonnet execute). **Compile mode — no implementation.**
This is an executable runbook, not strategy. Companion artifacts:
`PROJECTION_CONNECTION_STANDARD.md`, `REALITY_TEMPLATE_GRAPH.md`, and the four JSON
data files under `data/umh/{capabilities,projections,templates,roadmap}/`.

Trigger context: the first real organic EOS loop closed 2026-07-06 —
`action_1783367421127_b0ztpntev` went PENDING→APPROVED→EXECUTED through governed
mutation, creating a real task row (proof PR #201). P4-SYNC generalizes that one
proven loop across every projection.

## Architecture canon (binding)

- **UMH** = proprietary substrate + Cockpit mega-app + reality-template engine.
- **Cockpit** = the one proprietary command surface / super-app AND the projection
  mirror. It never absorbs projection-native UX.
- **EOS / LifeOS / CreatorOS** = standalone native projection apps that plug into
  UMH through published contracts (see the connection standard).
- **Antony / Beast / current repos** = the FIRST tenant-instance binding, not global
  truth. Every instance value enters through a variable, never a literal.
- Everything repeatable is a **RealityTemplate** candidate; workflows are
  **TemplateGraphs** (instance proof feeds the next instance).
- Deterministic spine first; AI enhances, never depends.

## 1. Current-state map

| Node/System | State (first-tenant binding) |
|---|---|
| **UMH substrate** | LIVE — governed_mutation → MutationRouter → GovernedExecutionSpine canonical; mesh dispatch live (relay+verdict); 13 gates green; registry truthful (1051 types) |
| **Cockpit** | PARTIAL — command surface + EOS approvals mirror (#186) live; LifeOS/CreatorOS mirrors are GAP |
| **EOS / EntrepreneurOS** | FIRST_LIVE_LOOP_CLOSED — read+approve+execute+proof live; W1/W2 hardening open on app PRs #3/#4; source `feature/company-system@9c8725f` |
| **LifeOS** | INTEGRATION_SHELL — source-dirty (WIP preserved `wip/2026-07-06-preserve`); 13 feature clusters mostly working; Clerk migration mostly committed; no UMH loop yet |
| **CreatorOS** | INTEGRATION_SHELL — source-current; 10 clusters; no UMH loop yet |
| **Beast tenant node** | executor role; C:\dev\dev\ repos = source of truth; daemon under op run, verdict secret live, 7 capabilities |
| **VPS runtime** | os-operator (1GiB, healthy, secrets injected), os-discord/webhook/browser/livekit; umh-mesh.service under op run |
| **1Password runtime** | LIVE — 4 vaults (substrate + per-projection); op run injection; **LyfeOS .env.tpl plaintext = open violation, rotation pending** |
| **GitHub/source** | main green through #201; app-repo PRs #3/#4 draft; OS review queue #193/#195/#196/#199/#200/#201 |

## 2–6. Inventories

Per-projection and cross-projection inventories are the JSON artifacts (single source
of truth, machine-checkable):
- Cross-projection capabilities: `data/umh/capabilities/cross_projection_capability_inventory.json`
- Connection matrix (per-projection slots): `data/umh/projections/projection_connection_matrix.json`
- **LifeOS** (13 clusters), **CreatorOS** (10 clusters), **EOS** (agent workforce, action
  proposals, CRM, task execution, company hierarchy, approval routes, auth, provider
  seams, W1/W2) are enumerated there and in the shipped inventory PRs (#193 LifeOS/CreatorOS
  clusters, #196 EOS deep seam). This doc does not duplicate them — it references them,
  per the essentialism rule.

## 7. UMH MVP operating loop (removes ChatGPT copy/paste)

Smallest path, deterministic spine + AI enhancement:
```
Cockpit voice/text intent
  → IntentSpec (deterministic parse; AI refines)
  → WorkGraph (TemplateGraph of TemplateInstances)
  → WorkPacket (one primitive unit of work)
  → agent/session dispatch (mesh or local)
  → approval (governed_mutation, human gate)
  → proof (envelope + server-truth read)
  → memory/template revision (CapabilityRevision)
  → status visible in Cockpit
```
Packet: **P4S-31** (skeleton). Acceptance: one intent produces a governed proof with
zero external copy/paste.

## 8. RealityTemplate / TemplateGraph ontology

Full ontology in `REALITY_TEMPLATE_GRAPH.md` and
`data/umh/templates/reality_template_taxonomy.json`. Core: Primitive → Invariant →
Variable → RealityTemplate → TemplateInstance → TemplateGraph → TemplateEdge, with
ProofRequirement and CapabilityRevision closing the learning loop. Essentialism:
one canonical home per capability; no speculative templates; N≥2 before extraction.

## 9. MVP gap matrix

| System | substrate gap | projection-native UX gap | adapter gap | template gap | proof/gov gap | tenant-instance gap |
|---|---|---|---|---|---|---|
| **UMH** | template registry (P4S-12); capability manifest (P4S-11) | — | — | RT extraction from EOS loop | intent→proof MVP loop (P4S-31) | — |
| **Cockpit** | — | mirror panels for LifeOS/CreatorOS (P4S-30) | — | — | — | — |
| **EOS** | — | — | send_email provider (P4S-40, held) | agent-chat-action template (blocked on W4) | task_id backfill (P4S-21) | app W1/W2 boot/claim guards (app #3/#4) |
| **LifeOS** | reflections→memory substrate | — | — | gamification templates | full governed loop (P4S-22) | source-dirty WIP + secret rotation |
| **CreatorOS** | — | — | — | publish-approval template | full governed loop | stale pg_dump disposition |

## 10. WorkGraph + packet bundle

Full packetized plan (id, objective, deps, files, tests, proof, rollback, stop
conditions, executor, lane, merge order) in `data/umh/roadmap/p4_sync_workgraph.json`.

**Merge order (binding):** app-repo `MERGE-GATE-0` (W1 #3 + W2 #4, operator-merged and
verified) → substrate packets P4S-1x → adapter/read-surface P4S-2x → templates P4S-3x →
**provider packet P4S-40 LAST**, hard-held until MERGE-GATE-0 verified.

**Lanes:** A (Sonnet, mechanical read surfaces/mirrors) · B (Opus, substrate registry +
MVP loop) · C (Opus, LifeOS loop instance) · D (Opus, provider — HELD).

## Hard constraints (enforced by this campaign)

No implementation in compile mode · no Antony/Beast as global truth · no projection UX
collapse into Cockpit · no blind code copy projection→UMH · no duplicated durable
capability without classification · **no provider execution until W1/W2 merged+verified** ·
no plaintext secrets · no unregistered mutations · no destructive Beast ops · no fake data
unless owner-approved and labeled.
