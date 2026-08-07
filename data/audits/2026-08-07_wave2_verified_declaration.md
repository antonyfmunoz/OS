# Wave 2 — Verified Execution Declaration (structural correction, round 8)

Closes the repeated integration-Task execution-kind invariant **structurally**,
after seven review rounds each closed a different pointwise instance of it.

## The defect class

    AUTHORITY was integrity-checked, but the DECLARATION identifying what that
    authority governs was re-read from mutable state at every consumer.

`scenario_map.json`'s `integration_task_id` is an unauthenticated field, while
the authority path digest-verifies that same field. Retarget it and the
DECLARATION moves while the AUTHORITY correctly refuses — so every gate keyed off
the declaration silently skips, the write-boundary guard disarms for the real
Task C, and a `worker` row becomes durable. `execution_kind` is immutable, so the
row is permanent and it dispatches to a real model worker.

Six rounds hardened *consumers* of the declaration. The seventh moved the
declaration itself. Round 8 removes the re-read.

## The invariant

> A VERIFIED TASK-EXECUTION DECLARATION IS CREATED ONCE FROM AUTHENTICATED RUN
> AUTHORITY AND CARRIED INTO ATTEMPT CREATION.

## Design

| Element | Home |
|---|---|
| Type | `records.VerifiedExecutionDeclaration` (frozen dataclass) |
| Sole constructor | `field_scenario_map.build_verified_declaration()` |
| Production build site | `FieldControlPlaneDriver.__init__` (once per run) |
| Write boundary | `ExecutionAttemptStore.create_attempt_idempotent` → `_assert_declared_kind` |
| Sealed-refusal mode | `ExecutionAttemptStore.seal_attempt_creation` |

The declaration is **recomputed from canonical plan/packet lineage**, never read
from the map's field. It is a **frozen value, not an accessor** — an accessor
re-derives per call, so a file mutated after validation still changes the answer,
which is precisely the bypass. Attaching is one-way and single-shot: replacing or
clearing it raises.

### Digest coverage (source-verified)

`binding_digest` (`field_scenario_map.py:514-533`) hashes
`binding.match_fields() | {run_id, candidate_sha}` together with
`{k: mapping[k] for k in SEMANTIC_LABELS}` — and `SEMANTIC_LABELS` includes
`integration_task_id` (`field_task_scope.py:79,82`). So the declaration's digest
covers both the run identity and the mapping it asserts.

### DECLARATION ≠ AUTHORIZATION

The builder deliberately does **not** call `resolve_canonical_grant`, and
`_lineage_records()` **excludes the grant ledger by name** (not by list index).

This is a separation, not a weakened check. Measured against the real field
fixture — whose grant is ACTIVE but 0.1 days past `expires_at` — an earlier
grant-gated builder failed to construct, Task C became UNDECLARED, and a
`C + worker` row persisted: the original defect through the expiry door.

Grant state may stop composition from RUNNING (DENIED/UNRESOLVED ⇒ **no**
Attempt). It may never change a Task's durable execution class.

### Unbuildable ⇒ sealed, not unarmed

If lineage cannot be resolved there is no declaration to enforce. An unarmed
store is **not** a safe default: measured with the plan ledger destroyed, a
direct write persisted `C + worker`. So the driver seals the write boundary and
**all** attempt creation is refused. A run that legitimately has no composition
(no scenario map, or no execution binding — an ordinary non-candidate run) has no
declaration *error* and therefore never seals.

## Former declaration reads — disposition

| Site | Class | Disposition |
|---|---|---|
| `_build_verified_declaration` | 1 — authoritative creation | recomputes lineage; never reads the field |
| `_declared_integration_packet_id` | was 3 | now a pure snapshot read |
| `_declared_execution_class_for` | was 3 | now a pure snapshot read |
| `_validated_integration_packet_id` | was 3 | AUTHORITY only; identity projects from the snapshot |
| `field_failure_policy` `_SCENARIO_KEYS` | 2 — diagnostics | failure-injection targeting only; decides no execution kind |
| `verification.verify_attempt(integration_task_id=…)` | caller parameter | zero production callers (pre-existing) |

**Category 3 (unsafe re-derivation used for safety behavior): ZERO.**

## Evidence

- Tamper matrix — 15 cases (retarget to A/B/fabricated/empty, corrupt/replace map,
  truncate/revoke/expire/delete/rename grants, frontier drop, candidate & run
  mismatch, digest tamper, id swap): declaration **invariant** in all 15; `C+worker`
  refused in all 15.
- Race (t0 build → t1 mutate map+grants+packets → t2 create): declaration
  unchanged, `C+worker` refused.
- Direct-persistence adversarial: `C+worker` refused; poisoned pre-existing
  `C+worker` row refused on idempotent return and **preserved unmutated** as
  evidence.
- Valid matrix: `A/B/D + worker` allowed; `C + composition` allowed;
  `C + worker` impossible; undeclared→composition refused.
- Mutations: **18/18 killed, zero survivors** — including the owner's most
  important mutant (keep all six prior pointwise defenses, remove only the
  write-boundary check ⇒ a real direct-persistence test fails).
- Full Wave 2 suite: **1575 passed**, 0 failed.
- All **18** gates pass; type registry audit truthful (1163 entries).

## Final architecture

ONE declaration authority · ONE write-boundary invariant · multiple optional
defense-in-depth checks. Not seven separate authorities.

The surviving pointwise checks (`_composition_task_predicate`,
`_authority_records_present`, `_validated_integration_packet_id`) are retained as
**defense-in-depth and observability** — they no longer carry the safety
invariant, and none of them re-derives the declaration.

## Behaviour deliberately changed (round 8)

Two prior behaviours were **superseded**, not regressed — both strictly stronger:

1. **Corrupt scenario map** previously refused the ENTIRE frontier (an
   availability cost the code documented as "accepted"). The declaration no longer
   comes from the map, so Task C stays recognised, `C+worker` is still refused, and
   ordinary Tasks are no longer starved.
2. **Non-candidate-shaped targets dir** previously refused at admission only, so a
   caller bypassing the scheduler still persisted `C+worker`. It now seals the
   durable write boundary, which no caller can bypass.
