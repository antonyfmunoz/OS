# Phase 96.8AC — Execution Authority Engine Proof

## What This Proves

A plan may propose action, but only authority can permit execution.

This phase builds the structural boundary between the planning layer
(which is purely epistemic — it models but never executes) and the
execution layer (which produces real WorkPackets with real effects).

The Execution Authority Engine evaluates proposed actions across 14
dimensions and produces a deterministic, hash-verified AuthorityDecision
that either permits or denies WorkPacket creation.

## Planning vs Authority vs Execution

Three distinct layers with hard boundaries:

### Planning (Phase 96.8Z)
- Produces `ExecutionPlanningCandidate` with action graphs
- Models proposed actions, risk envelopes, dependencies
- CANNOT invoke runtime, use wallets, access credentials
- Purely epistemic — hypotheses about action, not action itself

### Authority (Phase 96.8AC — this phase)
- Evaluates planning candidates against authority policies
- Checks environment, capability, risk, confidence, proof requirements
- Produces `AuthorityDecision` with deterministic hash
- Gates whether a WorkPacket can be created
- Does NOT execute — only permits or denies

### Execution (future phases)
- Takes authorized WorkPackets and executes them
- Bounded by the authority decision's class and conditions
- Produces execution proofs and transformation ledger records

## Authority Classes (7 levels)

| Class | Rank | Meaning |
|-------|------|---------|
| deny | 0 | Structurally forbidden, no override |
| read_only | 1 | May read, never write or mutate |
| propose_only | 2 | May propose for review, no execution |
| notify_execute | 3 | Execute and notify, no pre-approval |
| approve_execute | 4 | Requires system or founder approval before execution |
| supervised_execute | 5 | Requires human supervision during execution |
| autonomous_execute | 6 | May execute without human involvement |

## Why Financial/Wallet Actions Default Deny

Financial and wallet actions are in `STRUCTURALLY_DENIED_ACTIONS` — a
hardcoded frozenset. This is NOT configurable. No runtime override, no
config file, no environment variable can unlock these actions.

Rationale:
- Pre-revenue system — no financial execution is needed
- Financial errors are irreversible
- Wallet access creates supply chain attack surface
- The cost of a false negative (blocking a valid financial action) is
  near zero; the cost of a false positive (permitting an unauthorized
  financial action) is catastrophic
- Unlocking requires a code change, which means git history, review,
  and audit trail

## Why Local GUI Requires Environment Authority

GUI actions (browser_execution, chrome_launch, visible_gui_interaction,
computer_use_extraction, desktop_automation) require:

1. An environment specification (`required_environment_type`)
2. A matching `EnvironmentAuthority` with `can_own_gui=True`
   and `can_execute_browser=True`
3. The environment's `max_risk_class` must accommodate the action's risk

This prevents:
- VPS (no GUI) from attempting browser actions
- Misrouted GUI commands to wrong environment
- Unauthorized desktop automation

The `SUPERVISED_EXECUTE` authority class ensures a human is present
for all GUI execution, with `FOUNDER_APPROVAL` required.

## How This Prepares Real Autonomous Execution

The authority engine is the gatekeeper for safe autonomy escalation:

1. **Workstation/Jarvis**: The Windows desktop environment registers
   as `local_windows_desktop` with `can_own_gui=True`. The authority
   engine permits `SUPERVISED_EXECUTE` for browser actions in that
   environment, with founder visual confirmation.

2. **Onboarding Pipeline**: Safe ingestion actions
   (`safe_doc_extraction`, `ingestion_candidate_creation`) get
   `APPROVE_EXECUTE` — system can approve without founder intervention.
   This enables the one-command Discord ingestion pipeline from 96.8AB.

3. **Autonomy Escalation Path**:
   - Phase 1: Everything is `SUPERVISED_EXECUTE` or lower
   - Phase 2: Proven-safe actions graduate to `NOTIFY_EXECUTE`
   - Phase 3: Battle-tested actions graduate to `AUTONOMOUS_EXECUTE`
   - Financial/wallet actions NEVER graduate — they stay `DENY`

4. **Confidence Gating**: Actions below 0.7 confidence are blocked
   regardless of authority class. This prevents low-confidence plans
   from producing execution.

## Evaluation Dimensions

1. **Action type** — structural deny check
2. **Capability** — adapter must declare the capability
3. **Adapter** — must be configured and registered
4. **Environment** — must exist and have appropriate authority
5. **Worker/runtime** — implicit via environment
6. **Data sensitivity** — high sensitivity raises risk class
7. **Reversibility** — irreversible actions are HIGH risk
8. **Cost** — >$100 estimated cost is HIGH risk
9. **External mutation** — any external mutation is HIGH risk
10. **Financial risk** — >0.5 is CRITICAL
11. **Credential risk** — >0.5 is CRITICAL
12. **Recursive autonomy risk** — >0.3 is CRITICAL
13. **Confidence** — below 0.7 threshold blocks execution
14. **Proof requirements** — recorded as conditions

## Test Coverage

54 tests across 14 test classes:
- Read-only authority (4 tests including all-action sweep)
- Safe ingestion authority (3 tests with adapter verification)
- GUI execution authority (4 tests including all-action sweep)
- Financial denial (6 tests including all-action structural check)
- Credential denial (3 tests)
- Recursive autonomy denial (2 tests)
- Missing authority (4 tests)
- Proof requirements (2 tests)
- Confidence threshold (2 tests)
- Deterministic decision hash (2 tests)
- Risk classification (5 tests)
- Environment risk bounds (1 test)
- Authority class ranking (3 tests)
- Planning candidate integration (3 tests)
- Destructive operations (5 tests)
- Serialization (5 tests)

## Files

### New Modules
- `core/governance/execution_authority_engine_v1.py`

### Authority Proof Examples
- `data/runtime/execution_authority_proofs/read_only_query_authority.json`
- `data/runtime/execution_authority_proofs/drive_docs_ingestion_authority.json`
- `data/runtime/execution_authority_proofs/denied_financial_execution_authority.json`
- `data/runtime/execution_authority_proofs/supervised_gui_execution_authority.json`

### Tests
- `tests/test_execution_authority_engine_v1.py`

### Proof Report
- `docs/system/phase968ac_execution_authority_engine_proof.md`

## Next Gate

W0_WORKPACKET_EXECUTION_GATE_PROOF
