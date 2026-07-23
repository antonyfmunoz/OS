# Wave 2 — Session-1 Field Qualification Runbook

The Wave 2 slice is built and deterministically qualified (C1–C7 deterministic
layer). This runbook is the exact procedure for the LIVE Session-1 field
qualification, which requires owner-gated resources not available to an
autonomous agent run:

- **candidate Clerk origin + candidate secrets** (owner-provisioned; the
  candidate stack authenticates a real principal/tenant/membership);
- **the Beast Windows executor** with the mesh daemon in Session 1 (visible
  Chrome — the Browser Verification Law prohibits headless/SSH-Session-0);
- **real Claude CLI subscription quota** for ~20 agent invocations
  (4 workers × [1 smoke + 1 failure-qual + 3 green passes]).

Per the wartime order's stop condition, the live passes stop for the owner to
supply these. Everything below is ready to run once they are.

## Prerequisites (owner-supplied)

1. `UMH_CANDIDATE_ORIGIN` resolvable, or a tailnet DNS name for `tailscale serve`.
2. Candidate secrets on the VPS (`services/.env`) with the Clerk candidate origin.
3. `UMH_W2_DISPATCH_SECRET` allowlisted in `infra/candidate/make_candidate_env.py`
   (add `"UMH_W2_DISPATCH_SECRET"` to the allowlist — it is run-scoped, not a
   production secret).
4. Beast reachable (verified: `100.74.199.102`, mesh node `windows-desktop`),
   mesh daemon running in the interactive desktop session.
5. `CLAUDE_CODE_OAUTH_TOKEN` resolvable on the VPS host for the workers.

## Built and verified (no owner resources needed)

- **Enforced host isolation** — LIVE VERIFIED: `bwrap 0.9.0` hides `/opt/OS`
  from the worker mount namespace; env scrub strips all credentials.
  `python3 scripts/wave2_attempt_runner.py --spool-root X --preflight-only`.
- **Fixture app** — `infra/fixture/make_fixture_app.py` emits a green FastAPI +
  JS + pytest app (6 tests green at base) with the seeded A/B/C/D objective.
- **Acceptance matrix** — `scripts/wave2_matrix_report.py`: 47 deterministic
  rows PASS (101 backend tests). Vitest + field rows FIELD_PENDING.
- **Host attempt runner** — `scripts/wave2_attempt_runner.py`: spool →
  bwrap-isolated worker → signed result, integration-tested with a stubbed
  worker (no quota spent).

## The 30-step Session-1 journey (per pass)

Extend `scripts/wave1_field_dispatch.py` → `wave2_field_dispatch.py` with
subcommands `preflight | deploy-candidate | seed-fixture | start-runner | smoke |
run | inject-failure | reconcile | teardown`, and `wave1_field_collector.py` →
`wave2_field_collector.py` with the 30-step journey (w01–w30). Concrete anchors
are the w2-* testids shipped in C6:

w01 Session-1 + single-daemon proof · w02 fresh candidate + fixture (zero
attempts) · w03 Clerk auth · w04 principal/tenant proof · w05 type fixture
objective · w06 plan compiles (`wg-plan-root`) · w07 inspect plan · w08 Tasks
A–D non-executable · w09 approve PLAN via HUD (`wg-approve-btn`) · w10 banner
`PLAN APPROVED — EXECUTION NOT STARTED` + zero attempts · w11 type "Execute the
approved plan" · w12 chat surfaces the decision (`w2-exec-card-root`), NO
execution · w13 prove zero attempts pre-HUD · w14 HUD execution row
(`wg-approval-row[data-source-type="execution_authorization"]`) · w15 authorize
(`w2-execution-decision` → `w2-exec-approve-btn`) · w16 A+B RUNNING concurrently
(two `w2-execution-attempt[data-status="running"]`, distinct task ids) · w17 C
blocked (`w2-execution-attempt[data-task-id=C][data-status="blocked"]`) · w18 A,B
verified · w19 C reconverges after both · w20 preview live · w21 D distinct
verifier role · w22 D browser probe (Session-1 + real visible Chrome) · w23
collector's own visible-Chrome fixture witness (type "alpha", results render) ·
w24 Proof (`w2-proof-link`) · w25 Tasks complete only after Proof · w26
same-thread report in the ORIGINAL conversation · w27 Work Detail lineage · w28
refresh + full Chrome restart persistence · w29 zero prod deploy + /opt/OS
unchanged + no secrets in evidence · w30 cleanup (sandboxes clean, spool drained,
Tailscale serve restored).

## Qualification bar

- 1 smoke pass (abbreviated) + 1 failure-qualification pass (`inject-failure`
  `--variant tools-revoked-a`: A1's tool policy revokes Edit/Write → real worker
  genuinely cannot commit → C stays blocked, no false Proof → retry from
  `w2-execution-retry` → A2 without revocation → graph continues) + **3
  consecutive full green passes**.
- reconciliation ≥ 0.90; zero orphan 5xx; zero duplicate active attempts;
  exactly-2 concurrency (A/B overlap); zero attempts before authorization
  decided_at; C.started > max(A,B verified); exact commit binding; Proof before
  completion; zero unredacted secrets in evidence; `/opt/OS` HEAD unchanged;
  sandboxes cleaned; zero production deploy (no FLY_/GH_ key in any env audit).
- Heavy evidence gitignored under `/var/lib/umh/candidates/wave2/<sha>/` with
  sha256s in a committed manifest.

## After qualification

Regenerate `scripts/wave2_matrix_report.py` (field rows → FIELD_QUALIFIED),
update the PR with the 3 pass IDs + reconciliation scores + Proof manifest, run
the adversarial divergence review (§XVI), and only then mark the PR ready.
**Do not merge. Do not deploy production.**
