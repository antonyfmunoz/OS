# Wave 2 — Security Incident Closure Report (R0 containment)

**Incident:** run-scoped dispatch secret written in cleartext to a runner launch log
**Date:** 2026-07-23
**Candidate at time of incident:** `221b41717673`
**Head at containment:** `57c266b380cac6ec982d50088f2aa0f95e704f76`

**OUTCOME: CREDENTIAL ROTATION NOT REQUIRED.**
Only an ephemeral, run-scoped dispatch secret was exposed. No non-ephemeral
credential left its approved source.

This report contains **paths, hashes, timestamps and boolean findings only**.
No secret value appears here, and none may be added.

---

## 1. What happened

`start-runner` launched the host attempt runner with an invalid shell construct:

```
exec UMH_W2_DISPATCH_SECRET=$(cat <0600 file>) <python> <runner> ...
```

`exec` does not accept variable-assignment prefixes. Bash never ran the runner and
reported the entire assignment — including the expanded value — as `not found`,
writing it to the run's launch log.

Two consequences:

1. The run-scoped `UMH_W2_DISPATCH_SECRET` was written to disk in cleartext.
2. **The runner never started in any invocation**, while `start-runner` reported
   `started: true` (it trusted that `Popen` forked).

Consequence 2 is why the blast radius stayed small: no worker, lease, or signed
artifact was ever produced.

## 2. Blast radius

The launch line places exactly **two** values into the child process:

| Value | Kind | Exposed? |
|---|---|---|
| `UMH_W2_DISPATCH_SECRET` | ephemeral, run-scoped, minted per run | **YES** |
| `UMH_STATE_DIR` | filesystem path (not a secret) | n/a |

All other arguments are paths and integers.

**`CLAUDE_CODE_OAUTH_TOKEN` was never on that line.** It reaches the worker only
through the process environment (`worker_claude_cli.py` `extra_allow` →
`scrub_worker_env`), never as an argv element. Verified: no command/argv
construction in the harness references it.

## 3. ANTHROPIC_API_KEY — investigated, NOT an exposure

A 108-character real Anthropic API key was found in seven `candidate.env` files
during the sweep. Investigated to conclusion:

| Question | Finding |
|---|---|
| Same key as the host's own `/opt/OS/services/.env`? | **Yes** — copied by the `make_candidate_env` allowlist, not minted or moved |
| Variable | `ANTHROPIC_API_KEY` |
| File mode / owner | `0600`, `root` |
| Inside the repo tree? | **No** (`/var/lib/umh/...`) |
| Inside the evidence/proof tree? | **No** |

Escape test — occurrences of the key value in each exposure surface:

| Surface | Count |
|---|---|
| Evidence / proof artifacts | **0** |
| Repo working tree | **0** |
| Git commits on this branch | **0** |
| PR #313 text | **0** |
| Shell history | **0** |
| Spool / launch logs | **0** |
| Docker logs | **0** |

The env-audit artifact records **names only** — verified: contains no `sk-ant`
value, 3 keys by name. This is the credential-injection design working as
intended. The key never left its approved source, so **no rotation is required**.

All seven `candidate.env` files were shredded during containment (containers are
torn down; the keys are no longer needed on disk).

## 4. Latent credential defect — never fired

Independent review found that `worker_home` derives from `dirname(worktree_path)`,
making it **shared across all leases**, with `~/.claude/.credentials.json` copied
in and never deleted. On the first real worker invocation this would have written
the OAuth credential to a shared directory that outlives teardown.

**It never fired.** Verified on disk:

| Check | Result |
|---|---|
| `.worker-home` directories (host-wide) | **0** |
| `.credentials.json` copies under candidate tree | **0** |
| Worker lease worktrees (`auto-*`) | **0** |
| Signed spool envelopes (inbox/outbox/quarantine) | **0** |
| Attempt ledgers containing rows | **0** |

The four `.git` entries under the candidate tree are all seeded **fixture** repos
from `seed-fixture` — confirmed by path — not worker leases.

Pausing before the first real invocation prevented an actual credential incident.
The defect is repaired under R1 (per-attempt private homes).

## 5. Containment actions

| Action | Result |
|---|---|
| Host attempt runner / control-plane driver | none alive |
| Candidate containers (`os-operator-candidate-w2`, `os-nginx-candidate-w2`) | removed |
| Fixture preview process | none existed |
| Tailscale Serve | restored to prior state — `No serve config` (snapshot was `{}`) |
| Dispatch secret (incident SHA `221b41717673`) | shredded |
| Dispatch secret (all remaining SHAs) | shredded — **0 remain host-wide** |
| `candidate.env` × 7 | shredded — **0 remain** |
| Stale spool logs / pids | removed — **0 remain** |
| Temp worker homes | **0 existed**; sweep confirms none host-wide |

Note: teardown only shreds the secret for the SHA passed to it, which left an
orphan from a prior SHA (finding SEC-W4). Caught by independent verification and
swept manually; the reachability fix lands in R1.

## 6. Exhaustive scan — exposed dispatch secret

Fingerprint used for correlation (not the value):
`sha256 = a59dea14e58f5387d63a3c9e14bf8b3f6d048e0862350a2a9007baa7b03f8a2d`

| Surface | Result |
|---|---|
| Candidate state (all 8 wave2 SHA dirs) | **0 hits** |
| Spool / evidence artifacts | **0 hits** |
| Proof artifacts | **0 hits** |
| Repo working tree | **0 hits** |
| Git commits on this branch (6) | **0 hits** |
| Git staged index / working diff | **0 hits** |
| PR #313 body + comments | **0 hits**; 0 distinct 64-hex tokens |
| Docker logs (both candidate containers) | **0 hits** |
| System logs (`journalctl`, 3h) | **0 hits** |
| Shell history | **0 hits** |

Gates: Gate 8 (secret patterns) **exit 0**; Gate 7 (credential injection) **exit 0**.

## 7. `/opt/OS` main untouched (Amendment clause 10)

| Check | Result |
|---|---|
| HEAD | `6952687274545911e29f1859b8e563199a2d2203` (Wave 0) — unchanged |
| Branch | `main` |
| Any source file I modified present in `/opt/OS` dirty set | **none** |
| Stray wave2 worktrees | **none** |

The only session-era path under `/opt/OS` is
`data/audits/proof/2026-07-23_wave2_field/` — the harness's designated evidence
output directory, not a source modification.

## 8. Boolean findings summary

| Assertion | Result |
|---|---|
| No Claude worker process ran | **TRUE** |
| No worker lease worktree created | **TRUE** |
| No `~/.claude/.credentials.json` copy in candidate/run paths | **TRUE** |
| No non-ephemeral credential in logs/state/artifacts/Git/PR/argv/Docker/shell history | **TRUE** |
| Prior dispatch secret absent from every process and file | **TRUE** |
| `/opt/OS` untouched | **TRUE** |
| Tailscale Serve restored to exact prior state | **TRUE** |
| **CREDENTIAL ROTATION REQUIRED** | **FALSE** |

## 9. Permanent fixes already landed

1. `env VAR=value cmd` replaces `exec VAR=value cmd`. Independent review
   reproduced 400 tight `/proc` samples during the launch window: **no cmdline
   exposure**; the secret lands only in the runner's `environ` (`0600`,
   owner-only). The old form was reproduced side-by-side and still leaks —
   the regression is genuinely closed.
2. `start-runner` verifies the runner is alive and announced `runner up:` before
   reporting `started: true`. Any surfaced launch output is redacted first
   (redaction applied **before** slicing — verified).
3. `_mint_run_secret` is atomic `O_CREAT|O_EXCL|0600` with post-hoc mode
   verification and fail-closed `RuntimeError`; `secrets.token_hex(32)`.
4. The worker provably cannot inherit `UMH_W2_DISPATCH_SECRET` —
   `scrub_worker_env` is an allowlist; scrubbed keys are
   `['CLAUDE_CODE_OAUTH_TOKEN', 'HOME', 'PATH']` only.

### Superseded by R1

The bare 64-hex redaction rule added during the incident fix is **withdrawn** — it
destroys legitimate sha256 artifact/package/scope hashes and image IDs
(finding SEC-C1). Replaced by exact-value + typed-credential redaction inside the
one-way evidence-finalization pipeline.

## 10. Status

**INCIDENT CLOSED — NO ROTATION REQUIRED.**

Residual work tracked in the repair ledger: R1 (per-attempt homes, secret-shred
reachability, evidence pipeline).
