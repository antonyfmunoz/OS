# Wave 2 — Owner Preflight Table + Cost Gate

The field harness is built and proven runnable with no quota
(`scripts/wave2_harness_selfcheck.py` → 8 PASS / 0 FAIL / 1 OWNER_GATED). This
document reports the TRUE owner gates (order step 7) and the exact cost-gate stop
before the first real Claude worker (order step 8).

## Preflight table (order step 7)

Only genuine owner actions are listed as such. Resources that already work are
marked READY and must NOT be reprovisioned.

| RESOURCE | CURRENT STATE | EVIDENCE | OWNER ACTION REQUIRED | EXACT ACTION |
|---|---|---|---|---|
| Host isolation (bwrap) | READY | `bwrap 0.9.0`; preflight hides `/opt/OS` from worker namespace | none | — |
| Fixture app | READY | `make_fixture_app.py` → 6 tests green + A/B/C/D objective | none | — |
| Signed dispatch spool | READY | delivery + bad-signature quarantine verified | none | — |
| Control-plane loop | READY | full A/B→C→D rehearsal green (stub worker, no quota) | none | — |
| Dispatcher (9 subcommands) | READY | all assemble under `--dry-run` | none | — |
| Run-scoped dispatch secret | READY | minted 0600/64-hex, idempotent, shredded at teardown; NOT a production secret, NOT in the candidate allowlist | none | — |
| Clerk origin / auth | READY | candidate origin resolves via tailnet DNS; reuses the Wave-1 dev Clerk instance + JWKS (public keys, no secret key server-side) | none | — |
| Candidate secret allowlist | READY | `make_candidate_env.py` allowlist (auth + LLM + identity only; mesh/Discord/Fly/GitHub hard-denied) is reused as-is | none | — |
| Beast executor | READY | `windows-desktop` (100.74.199.102) active on the tailnet | confirm mesh daemon is up in the interactive Session-1 console before `run` | (Beast) ensure the "UMH Node Daemon" scheduled task is running in Session 1 |
| Tailscale serve | READY (cert-gated) | snapshot/restore inherited from wave1; HTTPS on :10443 | enable tailnet HTTPS certs IF not already enabled (deploy-candidate probes + reports) | Tailscale admin → DNS → HTTPS Certificates (one-time, only if the deploy cert-probe reports unavailable) |
| OAuth token to worker | VERIFY-AT-RUN | resolved by the host runner from its CC ancestor at worker time; not resolvable in a bare shell (expected) | none — verified automatically at `start-runner` | — |
| **Real Claude quota** | **OWNER-GATED** | the workers make real Claude CLI calls (subscription) | **authorize the quota spend** | see the cost gate below |

The only unconditional owner action is authorizing the real Claude quota spend.
The Tailscale-cert row is conditional (only if the deploy cert-probe reports HTTPS
unavailable) and the Beast-daemon row is an operational confirmation, not
provisioning.

## Cost gate (order step 8) — STOP before the first real worker

The harness stops here and reports the exact parameters. All values are
code-verified (not estimated):

| Parameter | Value | Source |
|---|---|---|
| Candidate SHA | the exact `git rev-parse --short=12 HEAD` of this branch at run time (bound into every dispatch + proof) | dispatcher `_candidate_sha` |
| Max real worker invocations | **~20** across the full bar: smoke (~2) + failure-qual (~6, incl. 1 retry) + 3 green passes (4 tasks × 3 = 12) | 4 tasks/pass (A,B,C,D), `max_attempts_per_task=2` |
| Max turns per invocation | **30** | `scheduler.py:301` (`max_turns: 30`) |
| Timeout per invocation | **600 s** (10 min) | `scheduler.py:301` (`timeout_seconds: 600`) |
| Max retries per task | **2** attempts total (1 retry) | grant `max_attempts_per_task=2` |
| Max parallelism | **2** concurrent implementation workers (A,B); C and D run alone | `AttemptScheduler(max_concurrency=2)` |
| Cost measurability | **cost_status="unknown"** — Wave 2 makes NO USD-enforcement claim; boundedness is enforced by turns × timeout × attempts × parallelism (`budget_enforcement="time_turn_attempt"`) | `records.py:134-137` |

**Worst-case bound:** ≤ 20 invocations × 30 turns × ≤ 600 s, ≤ 2 in flight at
once. There is no USD ceiling claim; the hard bound is time/turn/attempt/
parallelism, enforced by the scheduler and the worker adapter.

### Exact owner authorization sentence

> "Authorized: spend real Claude Code subscription quota for the Wave 2 Session-1
> field qualification on candidate SHA `<sha>` — up to 20 worker invocations, 30
> turns and 600 s each, at most 2 concurrent, for one smoke + one
> failure-qualification + three green passes."

Do NOT consume real quota before that sentence (or an equivalent explicit owner
order) is given.

## Current status language

```
WAVE 2 DETERMINISTIC LAYER:   OPERATIONAL
WAVE 2 FIELD HARNESS:         BUILT + REHEARSED (no quota) — RUNNABLE
WAVE 2 SESSION 1 FIELD LAYER: NOT RUN
REVIEW CLOSURE:               <pending independent review resolution>
MERGE:                        PROHIBITED
```
