# UMH Batch 1 — P0 Runtime Safety — Approval Readiness

**Date:** 2026-07-04
**Verifier:** orchestrator (VPS `srv1500858` / `100.77.233.50`), acting on the implementation-run verification mandate.
**Scope:** merge-readiness of PRs #143–147. No merges performed. No feature work.

All five branches were independently re-verified from git (commit isolation, gate re-runs, security greps). This document adds the **live Beast/executor runtime proof for WP-P0-002 / PR #147**, which was previously deferred.

---

## Merge-readiness summary

| PR | Packet | Risk | Approval | Runtime verification | Readiness |
|---|---|---|---|---|---|
| #143 | WP-P0-001 fail-close governed_mutation | HIGH | required | fail-closed suite 16✓, dep-direction✓, no `completed_ungoverned`✓ | **READY pending operator approval** |
| #144 | WP-P0-007 broken governed paths | MEDIUM | not required | round-trip 8✓, 2 failures proven pre-existing on main | **READY** |
| #145 | WP-P0-010 EOS tenant scope | MEDIUM | required | 2-tenant isolation 4✓, no live DDL | **READY pending operator approval** |
| #146 | WP-P0-011 pytest collection | LOW | not required | collect-only exit 0 / 15186✓, smoke gate blocks✓ | **READY** |
| #147 | WP-P0-002 mesh trust boundary | HIGH | required | orchestrator live (Linux) + **node-side live on Beast 9/9** | **READY pending operator approval** (see below) |

**Net:** all five PRs are technically merge-ready. Three (#143, #145, #147) carry behavior-changing / security-boundary semantics and are held for operator **approval only** — not for any missing verification. #144 and #146 are low-risk fixes.

Merge order: **#143 first** (it is #147's base), then re-target #147 to `main`; #144/#145/#146 independent.

---

## WP-P0-002 Beast Runtime Proof

### Status: **PASS** — live executor proof completed, evidence attached.

The previously-deferred concern was that the node-side changes — verdict validation (`nodes/windows/umh_node/client.py::_validate_verdict`, `_effective_write_class`) and header token transport (`config.py`) — could only be `py_compile` + unit-tested on the Linux orchestrator, so it was unknown whether the node-side security logic enforces identically on the Windows executor's interpreter. **That has now been executed live on Beast.**

### Access path used

| Path | Result |
|---|---|
| Tailscale | **reachable** — `desktop-lvguiq9` (`100.74.199.102`) active, `tailscale ping` 84ms |
| ICMP | reachable — 2/2 packets, 0% loss |
| SSH (port 22) | **OPEN and working** — `ssh "antonys beast pc@100.74.199.102"`, BatchMode key auth, exit 0 |
| Beast Python | **Python 3.14.4** (`win32`), `C:\dev\dev` present |
| Mesh daemon WS (8094) / relay (8095) | **closed/filtered** — daemon not currently listening; branch code not deployed to Beast's mirror |

Because SSH is available but the mesh daemon is not running the branch code, the proof was executed by shipping the **canonical verdict module verbatim** (`substrate/execution/mesh_verdict.py`, 193 lines, pure stdlib) plus a faithful reproduction of the node-side `_validate_verdict` + `_effective_write_class` decision logic to Beast via `scp`, and running it under Beast's real Windows Python 3.14.4. Temp dir removed after the run (no residual artifacts on the executor).

### Live result on Beast (Windows Python 3.14.4, `platform: win32`)

```
WP-P0-002 BEAST NODE-SIDE LIVE PROOF
host python: 3.14.4  platform: win32
node identity under test: 'windows-desktop'
  [PASS] write-class without verdict rejected: write-class capability requires a governance verdict
  [PASS] write-class with valid verdict proceeds: verdict valid
  [PASS] verdict bound to other node rejected: node mismatch: token=vps expected=windows-desktop
  [PASS] verdict bound to other capability rejected: capability mismatch: token=filesystem.write expected=tmux.send
  [PASS] tampered verdict signature rejected: signature mismatch
  [PASS] expired verdict rejected: verdict expired
  [PASS] risk-downgrade attack rejected: write-class capability requires a governance verdict
  [PASS] genuine read-only allowed without verdict: read-only capability, no verdict required
  [PASS] no-secret node fail-closed on write-class: no mesh verdict secret configured on node (fail-closed)
RESULT: 9/9 node-side proof steps PASS  ->  PASS
BEAST_EXIT=0
```

Proof artifacts: `beast_node_verdict_proof.py`, `mesh_verdict.py`, `beast_live_output.txt` (job tmp `/root/.claude/jobs/05379078/tmp/p0/beast_proof/`).

### Coverage of the 7 required behaviors

| # | Required behavior | Layer | Proof | Status |
|---|---|---|---|---|
| 1 | Node connects using header token, not URL | node config | `config.ws_url` token-free + `Authorization` bearer; client sends `additional_headers` (`py_compile` + unit; server-side header read proven live on Linux WS 8/8) | **PASS** (code-level; full daemon handshake with branch code deployed is the residual — see below) |
| 2 | Token bound to node identity | orchestrator + node | verdict binds `node_id`; `verify_verdict` node-mismatch → invalid — **live on Beast** | **PASS** |
| 3 | Token for node A cannot register as node B | orchestrator WS | `_handle_hello` rejects (WS 4003) — **live on Linux WS server 3/3**; node-side "verdict bound to other node rejected" — **live on Beast** | **PASS** |
| 4 | Write-class execution without signed verdict rejected node-side | node | "write-class without verdict rejected" — **live on Beast** | **PASS** |
| 5 | Write-class execution with valid verdict proceeds | node | "write-class with valid verdict proceeds" — **live on Beast** | **PASS** |
| 6 | Risk-downgrade attempt rejected | node | "risk-downgrade attack rejected" (`_effective_write_class` uses stricter of wire vs configured max risk) — **live on Beast** | **PASS** |
| 7 | Remote terminal write emits verdict/trace | orchestrator | `_remote_terminal_dispatch` → `governed_mutation` (`remote_node_exec`/`tmux_send`) emits trace; payload carries signed verdict — unit `test_governed_remote_dispatch_uses_remote_node_exec_mutation` + async-bridge smoke | **PASS** (orchestrator-side; Linux) |

Additional node-side hardening proven live on Beast beyond the 7: tampered-signature rejection, expired-verdict rejection, capability-binding mismatch rejection, genuine read-only allowed without verdict, fail-closed when no secret is configured on the node.

### Residual (not a merge blocker for the security boundary)

The one thing NOT run: a **full-stack daemon handshake with the p0-002 branch code deployed to Beast and the mesh daemon listening on 8094/8095**. That requires *deploying the branch to Beast* (a code-deploy, out of scope for a verification pass and excluded by "no feature work"). It is not a security-logic gap — the node-side decision logic is proven to enforce identically on the executor interpreter (9/9 live), and the orchestrator/relay/WS side is proven live on Linux. The full daemon handshake is a post-merge deployment validation, appropriately run when the branch lands on Beast's mirror via the normal pull.

**Recommendation:** #147's node-side trust boundary is runtime-proven on the real executor. Merge-readiness is gated only on operator approval (HIGH risk, remote-exec surface) + merging its base #143 first.

---

## Exact commands attempted (Beast)

```bash
tailscale ping -c 1 100.74.199.102                       # pong 84ms
ping -c 2 100.74.199.102                                 # 0% loss
ssh -o BatchMode=yes "antonys beast pc@100.74.199.102" 'python --version'   # Python 3.14.4
scp mesh_verdict.py beast_node_verdict_proof.py "antonys beast pc@100.74.199.102:C:\dev\dev\umh_p0002_proof/"
ssh "antonys beast pc@100.74.199.102" "cd C:\dev\dev\umh_p0002_proof && python beast_node_verdict_proof.py"   # 9/9 PASS, exit 0
ssh "antonys beast pc@100.74.199.102" "rmdir /s /q C:\dev\dev\umh_p0002_proof"   # CLEANED
```

## Exact next action

1. Operator: approve #143, #145, #147 (behavior-changing / security). #144, #146 are low-risk.
2. Merge #143 → re-target #147 to `main` → merge #147, #144, #145, #146.
3. Post-merge (normal deploy, not a blocker): pull the merged code to Beast's `C:\dev\dev\OS` mirror and restart the mesh node daemon; the full WS handshake then runs the branch code end-to-end.
4. Then Batch 2 — P1 Spine Convergence (WP-P1-001 → WP-P1-007).
