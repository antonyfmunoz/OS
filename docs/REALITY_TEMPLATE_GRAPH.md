# RealityTemplate / TemplateGraph Ontology

Compiled 2026-07-06 as part of P4-SYNC (compile mode). Seed data:
`data/umh/templates/reality_template_taxonomy.json`. Implementation home (future,
packet P4S-12): `substrate/templates/` — types go through `canonical_types.py`
per the Type Coherence Law. Aligned with EPISTEMOLOGY.md: mastery decomposes into
primitives and capability templates; templates are `f(invariants, variables, context)`.

## The chain

```
Primitive → Invariant → Variable → RealityTemplate → TemplateInstance
    → execution → proof → CapabilityRevision → (better) RealityTemplate
```

| Concept | Definition | Rule that makes it real |
|---|---|---|
| **Primitive** | Smallest irreducible capability unit the substrate understands (Signal, Operation, WorkPacket, Approval, Proof, Trace) | L2 only (`substrate/types.py`); never projection vocabulary |
| **Invariant** | What must NOT change across instances — the contract making proof transferable | Stated as testable assertions; an invariant without a test is a wish |
| **Variable** | Declared, typed slots for instantiation (tenant_id, projection_id, table, allowlist, principal column) | ALL tenant/projection specificity enters here — Instance Context Law at the template layer |
| **RealityTemplate** | Named, versioned, provable pattern: primitives composed under invariants with declared variables | Created only from a pattern that EXECUTED with proof; N≥2 instances before abstraction/extraction |
| **TemplateInstance** | One variable binding for one tenant+projection, with its own proof record | No proof → not complete → cannot feed edges |
| **TemplateGraph** | DAG of TemplateInstances; workflows ARE TemplateGraphs | Cycles forbidden; revision loops go through CapabilityRevision, not back-edges |
| **TemplateEdge** | Typed connection `(producer.proof_field) → (consumer.variable)` | Edges carry proof, never raw trust; an unproven producer starves its consumers (fail-closed propagation) |
| **ProofRequirement** | What the template demands before an instance may complete: envelope ids, server-truth reads, row verification, gate output | Named per-template; the EOS loop's requirement (PENDING→APPROVED→EXECUTED chain + row verify + secret scan) is the reference |
| **CapabilityRevision** | Executed instance's proof + defects feed a template revision (invariant sharpened, variable added, gotcha recorded) | Templates improve ONLY through executed instances — the #197/#198 defects becoming standard requirements is the canonical example |

## Essentialism / no-redundancy rules (binding)

1. **One canonical home per durable capability.** A duplicate must be classified in
   the capability inventory (substrate / projection-specific / template) or converged.
2. **No speculative templates.** Zero-instance templates are forbidden; one-instance
   templates are *records* (status PROVEN_1_INSTANCE), not abstractions.
3. **N≥2 before extraction.** Code-level abstraction (factory, helper, base class)
   requires a second real instance — same rule the projection-read-surface
   discipline already enforces.
4. **Instance values never in template bodies.** Tenant, node, brand, product names
   bind through variables at instantiation.
5. **Proof gates edges.** A TemplateGraph may only advance across edges whose
   producer instance carries its ProofRequirement.
6. **Revision is append-only.** Template versions are immutable; a revision is a new
   version citing the instance proofs that motivated it.

## Worked example (the loop that closed today)

`RT-GOVERNED-PROPOSAL-LOOP`, instance `eos/<tenant>`:
variables bound (proposal_table=agent_actions, allowlist={create_task,create_document},
principal_column=approved_by, ...); invariants held through two live defect discoveries
(fail-closed both times); ProofRequirement satisfied by PR #201; CapabilityRevision
already applied — "registered MutationSpec" and "FK-safe principal stamping" were
promoted from bugfixes to template invariants. Next instances: LifeOS (P4S-22),
CreatorOS (publish-content).
