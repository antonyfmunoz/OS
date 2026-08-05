# Scenario-map role resolution — canonical identity, not display text

**Date:** 2026-08-05
**Base SHA:** `36ae65677d9ac155333c259e5e90ff27203042fc`
**Scope:** field fixture/scenario-map role-resolution seam + its tests

---

## 1. The proven defect

Field run **`20260805T172351Z-p1`** (invocation 36/40) aborted before any Attempt
was created:

```
'backend_task_id' (title 'add note search backend endpoint') matched 0 plan nodes
— expected exactly 1; refusing an ambiguous target
```

`resolve_scenario_map` matched hard-coded fixture titles against LLM-generated
plan-node titles by exact case-folded equality. The planner emitted different
display text:

| Constant (`FIXTURE_NODE_TITLES`) | Planner output |
|---|---|
| `add note search backend endpoint` | `Add **the** note**-**search backend endpoint` |
| `add note search frontend ui` | `Add **the** note**-**search frontend UI` |
| `integrate and reconcile search branches` | `Integrate and reconcile **the** search branches` |
| `independently verify note search` | *(matched)* |

Three of four drifted by an inserted article and a hyphen. **The plan itself was
correct** — 6 nodes, 4 WorkPackets, correct substantive roles. A machine role
must never depend on an article an LLM chose.

## 2. The existing canonical identity (found, not invented)

Tracing fixture → plan node → Task → WorkPacket → scenario map showed the plan
node **already persists the machine role**:

```json
{
  "node_id": "node-47e04f536b64",
  "title": "Add the note-search backend endpoint",
  "semantic_label": "backend_task_id",
  "writable_path_scope": ["app/main.py", "app/store.py", "tests/test_search_api.py"],
  "workpacket_id": "wp-4e6d0137b686"
}
```

All four roles carry `semantic_label` matching `SEMANTIC_LABELS` exactly; the two
trailing non-task nodes carry none. **No second task model was created** — the
resolver was repointed at the identity that already existed.

## 3. Resolution order (as implemented)

1. **Canonical** — match `node.semantic_label == label`.
2. **Legacy fallback** — cosmetic-only title normalization, reached ONLY when
   *no* node in the plan carries any canonical label.
3. Require **exactly one** match.
4. **Fail closed** on zero, multiple, or normalized collision.

A plan that declares machine roles is **never** re-resolved by title: if any node
carries a canonical label and the requested role is absent, resolution refuses
rather than falling back (a conflicting machine role outranks title resemblance).

### Normalization — cosmetic only

Unicode NFKC · case folding · hyphen/underscore → space · punctuation → space ·
whitespace collapse · articles (`a`/`an`/`the`) dropped **as standalone words**.

Deliberately NOT used: substring, fuzzy similarity, embeddings, stemming, token
overlap, LLM adjudication. Every other word survives verbatim.

> Articles are dropped wherever they occur, not only leading. The observed drift
> (`Add **the** note-search…`) is mid-title, so a leading-only rule could not
> fold it. Word-level matching also means `theme` is never mistaken for `the`.

## 4. Observability

Every bind logs role, method (`semantic_label` | `normalized_title`), node_id,
packet_id, candidate count, raw title, normalized title. Refusals name the exact
reason and, for collisions, **both** colliding node ids. No silent fallback.

## 5. Verification

**Against the real failed-run records** — all four roles bind via
`method=semantic_label`:

```
backend_task_id      -> wp-4e6d0137b686
frontend_task_id     -> wp-17c878692c50
integration_task_id  -> wp-bc3dcf40112a
verification_task_id -> wp-77292d62b8ec
```

**Tests: 31 in `test_wave2_scenario_role_resolution.py`**, covering all 13
required properties: canonical binding despite capitalization / articles /
hyphenation / unrelated titles; legacy fallback for each cosmetic class; exact
legacy titles still work; substantive changes do not match; normalized collision
fails closed naming both nodes; missing role fails closed; a conflicting semantic
key cannot fall back; the map stores packet ids not display text; the designated
failure stays bound to the intended backend Task; no packet resolves without real
lineage.

**Mutation: 10/10 killed**, source restored byte-identically
(`816c02a69b790708…`).

| Mutant | Verdict |
|---|---|
| R1 exact-title-only restored (original defect) | KILLED |
| R2 canonical resolution removed | KILLED |
| R3 substring matching | KILLED |
| R4 first normalized match accepted | KILLED |
| R5 article handling removed | KILLED |
| R6 hyphen/space handling removed | KILLED |
| R7 over-normalizes substantive terms | KILLED |
| R8 falls back past a conflicting key | KILLED |
| R9 success with zero matches | KILLED |
| R10 binds the wrong node id | KILLED |

**R3 initially SURVIVED.** No legacy fixture title was a substring of another, so
swapping `==` for `in` changed nothing under test. Two directional substring
tests were added (superset title, and node title as a strict prefix of the
wanted); R3 then died. A green sweep whose mutants are equivalent proves nothing.

**Regression:** one pre-existing test
(`test_scenario_map_fails_closed_on_ambiguous_titles`) asserted the old
implementation's message `"matched 2 plan nodes"`. The **guarantee is unchanged**
— duplicate titles still fail closed — but the refusal now comes from the
collision branch and names both node ids. The assertion was updated to the
guarantee rather than the wording; it now also asserts both ids appear.

**Differential:** 23 failed at baseline, 23 failed after — **failure sets
identical, zero regressions**. Gates **15/15**.

## 6. Scope discipline

Changed: `substrate/execution/attempts/field_task_scope.py` (resolver +
normalizer), its new test file, and one message-coupled assertion.

Untouched: scheduler, grants, retry logic, WorkPacket execution, verifier
strictness, Proof rules, the deployed mesh hotfix, planner behavior. The
scenario-map cardinality requirement (exactly one match) is **unchanged** — the
change is *which key* proves identity, not *how many* matches are required.
